from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


@dataclass
class BrowserInfo:
    titulo: str
    url: str
    paginas_abertas: int


class BrowserSession:
    """Conexão a uma instância visível do Chrome via CDP.

    A sessão não fecha o Chrome do usuário. A Fase 2 usa a página ativa somente
    para o fluxo controlado de pesquisa de uma inscrição, sem emissão de guia.
    """

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222") -> None:
        self.cdp_url = cdp_url
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    def conectar(self) -> BrowserInfo:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_url)

        contextos = self._browser.contexts
        if not contextos:
            raise RuntimeError("Chrome conectado, mas nenhum contexto de navegador foi encontrado.")

        paginas = [pagina for contexto in contextos for pagina in contexto.pages]
        if not paginas:
            raise RuntimeError("Chrome conectado, mas nenhuma página está aberta.")

        # Preferir a página do FGTS Digital quando houver mais de uma aba.
        pagina_fgts = next(
            (pagina for pagina in reversed(paginas) if "fgtsdigital.sistema.gov.br" in pagina.url.lower()),
            None,
        )
        self._page = pagina_fgts or paginas[-1]

        return BrowserInfo(
            titulo=self._page.title(),
            url=self._page.url,
            paginas_abertas=len(paginas),
        )

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Chrome ainda não está conectado.")
        return self._page

    def fechar_conexao(self) -> None:
        # Não fecha o Chrome do usuário; encerra somente o cliente Playwright.
        if self._playwright is not None:
            self._playwright.stop()
        self._playwright = None
        self._browser = None
        self._page = None
