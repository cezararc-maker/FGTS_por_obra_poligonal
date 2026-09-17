from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

from .app import AppFGTS
from .browser_connection import BrowserSession
from .phase3_flow import executar_fase3
from .portal_flow import PortalFlowError, salvar_screenshot_erro


class AppFGTSFase3(AppFGTS):
    def __init__(self) -> None:
        super().__init__()
        self.title("FGTS por Obra/Poligonal — Modo TESTE Fase 3")
        self.btn_fase2.configure(
            text="FASE 3 — Selecionar e adicionar à guia",
            command=self._executar_fase3,
        )

    def _executar_fase3(self) -> None:
        if self.resultado is None or not self.resultado.valida:
            return

        item = self._item_selecionado()
        if item is None:
            messagebox.showwarning("Seleção", "Selecione uma inscrição na tabela.")
            return

        confirmar = messagebox.askyesno(
            "Confirmar Fase 3",
            "A automação irá operar UMA inscrição no Chrome visível.\n\n"
            f"{item.tipo_inscricao}: {item.inscricao}\n"
            f"Serviço: {item.servico}\n"
            f"Competência: {self.resultado.competencia}\n\n"
            "Ações permitidas nesta fase:\n"
            "• pesquisar a inscrição;\n"
            "• marcar o checkbox geral dos débitos retornados;\n"
            "• clicar em 'Adicionar à guia'.\n\n"
            "Ação BLOQUEADA: clicar em 'Avançar'.\n"
            "A automação para imediatamente após 'Adicionar à guia'.\n\n"
            "Deseja continuar?",
        )
        if not confirmar:
            self._registrar("Fase 3 cancelada pelo operador antes de qualquer ação no portal.")
            return

        self.btn_fase2.configure(state="disabled")
        sessao = BrowserSession()
        self.browser_session = sessao

        try:
            self._registrar("FASE 3 INICIADA — conectando ao Chrome dedicado...")
            info = sessao.conectar()
            self._registrar(f"Chrome conectado: {info.titulo} | {info.url}")

            resultado = executar_fase3(
                sessao.page,
                tipo_inscricao=item.tipo_inscricao,
                inscricao=item.inscricao,
                competencia=self.resultado.competencia,
                log=self._registrar,
            )

            total = resultado.total_itens if resultado.total_itens is not None else "não identificado"
            messagebox.showinfo(
                "Fase 3 concluída",
                "A seleção foi adicionada à guia com parada de segurança.\n\n"
                f"{resultado.tipo_inscricao}: {resultado.inscricao}\n"
                f"Competência: {resultado.competencia}\n"
                f"Total de itens informado pelo portal: {total}\n\n"
                "A automação PAROU após 'Adicionar à guia'.\n"
                "O botão 'Avançar' NÃO foi clicado.\n\n"
                "Confira visualmente no portal se o resumo/valor da guia foi atualizado.",
            )

        except Exception as exc:
            screenshot = None
            try:
                screenshot = salvar_screenshot_erro(sessao.page, Path.cwd())
            except Exception:
                pass

            detalhe = str(exc)
            if screenshot:
                detalhe += f"\n\nScreenshot local: {screenshot}"

            titulo = "Fase 3 interrompida"
            if not isinstance(exc, PortalFlowError):
                titulo = "Erro inesperado na Fase 3"

            messagebox.showerror(
                titulo,
                "A automação foi interrompida e NÃO continuará automaticamente.\n\n" + detalhe,
            )
            self._registrar(f"FASE 3 INTERROMPIDA: {exc}")
            if screenshot:
                self._registrar(f"Screenshot local do erro: {screenshot}")
        finally:
            sessao.fechar_conexao()
            self.browser_session = None
            self.btn_fase2.configure(state="normal")


def main() -> None:
    app = AppFGTSFase3()
    app.mainloop()


if __name__ == "__main__":
    main()
