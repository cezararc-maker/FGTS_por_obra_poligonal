from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Browser, Playwright, sync_playwright


@dataclass
class BrowserInfo:
    titulo: str
    url: str
    paginas_abertas: int


class BrowserSession:
    """Conexão segura de leitura a uma instância visível do Chrome via CDP.

    Nesta fase não navega, não clica e não altera o portal. Serve apenas para
    comprovar que o Python consegue enxergar a sessão do navegador dedicado.
    """

    def __init__(self, cdp_url: str = "http://127.0.0.1:9222") -> None:
        self.cdp_url = cdp_url
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    def conectar(self) -> BrowserInfo:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.connect_over_cdp(self.cdp_url)

        contextos = self._browser.contexts
        if not contextos:
            raise RuntimeError("Chrome conectado, mas nenhum contexto de navegador foi encontrado.")

        paginas = [pagina for contexto in contextos for pagina in contexto.pages]
        if not paginas:
            raise RuntimeError("Chrome conectado, mas nenhuma página está aberta.")

        pagina = paginas[-1]
        return BrowserInfo(
            titulo=pagina.title(),
            url=pagina.url,
            paginas_abertas=len(paginas),
        )

    def fechar_conexao(self) -> None:
        # Não fecha o Chrome do usuário; encerra somente o cliente Playwright.
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
            self._browser = None
