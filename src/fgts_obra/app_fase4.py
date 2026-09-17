from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

from .app import AppFGTS
from .browser_connection import BrowserSession
from .phase4_flow import executar_fase4
from .portal_flow import PortalFlowError, salvar_screenshot_erro


class AppFGTSFase4(AppFGTS):
    def __init__(self) -> None:
        super().__init__()
        self.title("FGTS por Obra/Poligonal — Modo TESTE Fase 4")
        self.btn_fase2.configure(
            text="FASE 4 — Consignado, vencimento e TAG",
            command=self._executar_fase4,
        )

    def _executar_fase4(self) -> None:
        if self.resultado is None or not self.resultado.valida:
            return

        item = self._item_selecionado()
        if item is None:
            messagebox.showwarning("Seleção", "Selecione uma inscrição na tabela.")
            return

        confirmar = messagebox.askyesno(
            "Confirmar Fase 4",
            "A automação irá operar UMA inscrição no Chrome visível.\n\n"
            f"{item.tipo_inscricao}: {item.inscricao}\n"
            f"Serviço: {item.servico}\n"
            f"Competência: {self.resultado.competencia}\n"
            f"Vencimento esperado: {self.resultado.vencimento_calculado:%d/%m/%Y}\n"
            f"TAG: {item.tag}\n\n"
            "Ações permitidas nesta fase:\n"
            "• executar o fluxo já validado até Adicionar à guia;\n"
            "• Avançar para Selecionar Débitos Consignado;\n"
            "• NÃO alterar a seleção do consignado;\n"
            "• Avançar para Definir Vencimento;\n"
            "• conferir o vencimento do portal;\n"
            "• preencher a TAG da planilha.\n\n"
            "Ação BLOQUEADA: Emitir Guia.\n"
            "Deseja continuar?",
        )
        if not confirmar:
            self._registrar("Fase 4 cancelada pelo operador antes de qualquer ação no portal.")
            return

        self.btn_fase2.configure(state="disabled")
        sessao = BrowserSession()
        self.browser_session = sessao

        try:
            self._registrar("FASE 4 INICIADA — conectando ao Chrome dedicado...")
            info = sessao.conectar()
            self._registrar(f"Chrome conectado: {info.titulo} | {info.url}")

            resultado = executar_fase4(
                sessao.page,
                tipo_inscricao=item.tipo_inscricao,
                inscricao=item.inscricao,
                competencia=self.resultado.competencia,
                vencimento=self.resultado.vencimento_calculado,
                tag=item.tag,
                log=self._registrar,
            )

            messagebox.showinfo(
                "Fase 4 concluída",
                "A etapa de vencimento/TAG foi preparada com parada de segurança.\n\n"
                f"{resultado.tipo_inscricao}: {resultado.inscricao}\n"
                f"Competência: {resultado.competencia}\n"
                f"Vencimento validado: {resultado.vencimento_portal}\n"
                f"TAG preenchida: {resultado.tag}\n\n"
                "A automação PAROU antes de 'Emitir Guia'.\n"
                "Confira visualmente os dados no portal.",
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

            titulo = "Fase 4 interrompida"
            if not isinstance(exc, PortalFlowError):
                titulo = "Erro inesperado na Fase 4"

            messagebox.showerror(
                titulo,
                "A automação foi interrompida e NÃO continuará automaticamente.\n\n" + detalhe,
            )
            self._registrar(f"FASE 4 INTERROMPIDA: {exc}")
            if screenshot:
                self._registrar(f"Screenshot local do erro: {screenshot}")
        finally:
            sessao.fechar_conexao()
            self.browser_session = None
            self.btn_fase2.configure(state="normal")


def main() -> None:
    app = AppFGTSFase4()
    app.mainloop()


if __name__ == "__main__":
    main()
