# -*- coding: utf-8 -*-
"""
PDFImageExtractor
-----------------
Extrai imagens de PDFs conforme um arquivo de configuração JSON.

Requer:
  pip install pymupdf

Suporta dois modos:
  - mode="embedded": extrai imagens embutidas (objetos) do PDF
  - mode="render": renderiza as páginas como imagens (ex.: para PDFs "escaneados")

Config JSON (exemplo ao final).
"""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Iterable, Tuple
from pathlib import Path
import re

import fitz  # PyMuPDF


@dataclass
class ExtractConfig:
    # Entradas
    input_dir: Optional[str] = None
    input_file: Optional[str] = None
    file_glob: str = "*.pdf"

    # Saída
    output_dir: str = "output"
    image_format: str = "png"  # "png" ou "jpg"
    overwrite: bool = False
    prefix_with_pdf_name: bool = True

    # Páginas / Seleção
    page_range: str = "all"    # "all" | "1-3,5,7-10"
    include_regex: Optional[str] = None  # filtra PDFs pelo nome
    exclude_regex: Optional[str] = None

    # Modo
    mode: str = "embedded"     # "embedded" | "render"

    # Render (se mode="render")
    dpi: int = 200
    render_alpha: bool = False  # manter transparência ao renderizar (só PNG)

    # Embedded (se mode="embedded")
    flatten_transparency: bool = True  # achatar transparência nas imagens extraídas

    def validate(self) -> None:
        if not self.input_dir and not self.input_file:
            raise ValueError("Informe 'input_dir' OU 'input_file' no JSON.")
        if self.image_format.lower() not in {"png", "jpg", "jpeg"}:
            raise ValueError("image_format deve ser 'png' ou 'jpg'/'jpeg'.")
        if self.mode not in {"embedded", "render"}:
            raise ValueError("mode deve ser 'embedded' ou 'render'.")
        if self.dpi < 72 and self.mode == "render":
            raise ValueError("dpi muito baixo para render: use >= 72.")

        # Normalizações
        self.image_format = "jpg" if self.image_format.lower() == "jpeg" else self.image_format.lower()


class PDFImageExtractor:
    def __init__(self, config_path: str, logger: Optional[logging.Logger] = None):
        self.config = self._load_config(config_path)
        self.config.validate()
        self.log = logger or self._default_logger()

        out = Path(self.config.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        self.log.debug("Config carregada: %s", self.config)

    # ---------------------- Infra ----------------------

    def _default_logger(self) -> logging.Logger:
        log = logging.getLogger("PDFImageExtractor")
        if not log.handlers:
            log.setLevel(logging.INFO)
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
            log.addHandler(ch)
        return log

    def _load_config(self, path: str) -> ExtractConfig:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ExtractConfig(**data)

    def _iter_input_files(self) -> Iterable[Path]:
        if self.config.input_file:
            p = Path(self.config.input_file)
            if not p.is_file():
                raise FileNotFoundError(f"Arquivo não encontrado: {p}")
            return [p]

        base = Path(self.config.input_dir)
        if not base.is_dir():
            raise NotADirectoryError(f"Diretório não encontrado: {base}")

        files = sorted(base.glob(self.config.file_glob))
        inc = re.compile(self.config.include_regex) if self.config.include_regex else None
        exc = re.compile(self.config.exclude_regex) if self.config.exclude_regex else None

        for f in files:
            if inc and not inc.search(f.name):
                continue
            if exc and exc.search(f.name):
                continue
            yield f

    @staticmethod
    def _parse_page_range(spec: str, page_count: int) -> List[int]:
        """Converte 'all' ou '1-3,5' em lista de índices zero-based."""
        if spec.lower() == "all":
            return list(range(page_count))

        selected: List[int] = []
        for token in spec.split(","):
            token = token.strip()
            if "-" in token:
                a, b = token.split("-", 1)
                start = max(int(a) - 1, 0)
                end = min(int(b), page_count)
                selected.extend(range(start, end))
            else:
                idx = int(token) - 1
                if 0 <= idx < page_count:
                    selected.append(idx)
        # Remover duplicatas mantendo ordem
        seen = set()
        unique = []
        for i in selected:
            if i not in seen:
                unique.append(i)
                seen.add(i)
        return unique

    @staticmethod
    def _safe_name(text: str) -> str:
        return re.sub(r"[^a-zA-Z0-9._-]+", "_", text)

    # ---------------------- API pública ----------------------

    def run(self) -> None:
        total_files = 0
        total_images = 0
        for pdf_path in self._iter_input_files():
            self.log.info("Processando: %s", pdf_path.name)
            try:
                n = self._process_pdf(pdf_path)
                total_images += n
                total_files += 1
                self.log.info("  -> %d imagem(ns) extraída(s).", n)
            except Exception as e:
                self.log.error("Erro ao processar %s: %s", pdf_path, e)

        self.log.info("Concluído. PDFs: %d | Imagens extraídas: %d", total_files, total_images)

    # ---------------------- Núcleo ----------------------

    def _process_pdf(self, pdf_path: Path) -> int:
        cfg = self.config
        out_dir = Path(cfg.output_dir)
        doc = fitz.open(pdf_path)
        pages = self._parse_page_range(cfg.page_range, doc.page_count)

        count = 0
        base_name = pdf_path.stem if cfg.prefix_with_pdf_name else ""

        if cfg.mode == "render":
            for i in pages:
                page = doc.load_page(i)
                zoom = cfg.dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(alpha=cfg.render_alpha)

                # aplicar matrix para DPI se necessário
                if cfg.dpi != 72:
                    pix = page.get_pixmap(matrix=mat, alpha=cfg.render_alpha)

                fname = self._make_filename(base_name, page_idx=i, img_idx=None, suffix="page")
                save_path = (out_dir / fname).with_suffix("." + cfg.image_format)
                if save_path.exists() and not cfg.overwrite:
                    self.log.debug("  - p.%d já existe, pulando (overwrite=False)", i + 1)
                    continue

                pix.save(save_path.as_posix())
                count += 1

        else:  # embedded
            for i in pages:
                page = doc.load_page(i)
                images = page.get_images(full=True)
                if not images:
                    self.log.debug("  - p.%d: sem imagens embutidas.", i + 1)
                    continue

                for j, img in enumerate(images, start=1):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)

                    # Trata transparência se solicitado
                    if pix.alpha and self.config.flatten_transparency:
                        pix = self._flatten_alpha(pix)  # converter para RGB

                    # Se ainda tiver alpha e formato escolhido for JPG, força remover alpha
                    if pix.alpha and self.config.image_format == "jpg":
                        pix = self._flatten_alpha(pix)

                    fname = self._make_filename(base_name, page_idx=i, img_idx=j, suffix="embedded")
                    save_path = (out_dir / fname).with_suffix("." + cfg.image_format)
                    if save_path.exists() and not cfg.overwrite:
                        self.log.debug("  - p.%d img.%d já existe, pulando (overwrite=False)", i + 1, j)
                        continue

                    pix.save(save_path.as_posix())
                    count += 1

        doc.close()
        return count

    def _make_filename(self, base_name: str, page_idx: int, img_idx: Optional[int], suffix: str) -> str:
        # Ex.: <pdfname>__page_001.png  ou  <pdfname>__page_001_img_002.png
        base = self._safe_name(base_name) if base_name else "pdf"
        p = f"{page_idx + 1:03d}"
        if img_idx is None:
            return f"{base}__{suffix}_{p}"
        return f"{base}__{suffix}_{p}_img_{img_idx:03d}"

    @staticmethod
    def _flatten_alpha(pix: fitz.Pixmap) -> fitz.Pixmap:
        """Remove canal alpha mesclando com fundo branco; retorna Pixmap RGB."""
        if not pix.alpha:
            # já é sem alpha
            return pix if pix.n < 5 else fitz.Pixmap(fitz.csRGB, pix)
        # Converte para RGB sem alpha
        rgb = fitz.Pixmap(fitz.csRGB, pix.width, pix.height)
        rgb.clear_with(255)  # fundo branco
        rgb.copy(pix)        # mescla
        pix = rgb
        return pix
