from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

from .app import AppFGTS
from .browser_connection import BrowserSession
from .phase5_flow import DownloadRelatorioTimeout, _reiniciar, executar_fase5
from .portal_flow import PortalFlowError, salvar_screenshot_erro


class AppFGTSFase5(AppFGTS):
    def __init__(self) -> None:
        super().__init__()
        self.title("FGTS por Obra/Poligonal — Modo TESTE Fase 5")
        self.btn_fase2.configure(
            text="FASE 5 — Emitir guia e baixar relatórios",
            command=self._executar_fase5,
        )

    def _executar_fase5(self) -> None:
        if self.resultado is None or not self.resultado.valida:
            return
        item = self._item_selecionado()
        if item is None:
            messagebox.showwarning("Seleção", "Selecione uma inscrição na tabela.")
            return

        confirmar = messagebox.askyesno(
            "Confirmar emissão da guia",
            "Esta etapa irá EMITIR de fato uma guia para UMA inscrição.\n\n"
            f"{item.tipo_inscricao}: {item.inscricao}\n"
            f"Serviço: {item.servico}\n"
            f"Competência: {self.resultado.competencia}\n"
            f"TAG: {item.tag}\n\n"
            "Depois da emissão, a automação irá capturar e salvar a própria guia, "
            "baixará o PDF do FGTS e, quando houver, o PDF do Consignado, e então clicará em Reiniciar.\n\n"
            "Deseja emitir esta guia?",
        )
        if not confirmar:
            self._registrar("Fase 5 cancelada pelo operador antes da emissão.")
            return

        self.btn_fase2.configure(state="disabled")
        sessao = BrowserSession()
        self.browser_session = sessao

        try:
            self._registrar("FASE 5 INICIADA — conectando ao Chrome dedicado...")
            info = sessao.conectar()
            self._registrar(f"Chrome conectado: {info.titulo} | {info.url}")

            resultado = executar_fase5(
                sessao.page,
                tipo_inscricao=item.tipo_inscricao,
                inscricao=item.inscricao,
                competencia=self.resultado.competencia,
                vencimento=self.resultado.vencimento_calculado,
                tag=item.tag,
                log=self._registrar,
            )

            numero = resultado.numero_guia or "não identificado"
            mensagem = (
                "Guia emitida e fluxo reiniciado com sucesso.\n\n"
                f"{resultado.tipo_inscricao}: {resultado.inscricao}\n"
                f"Competência: {resultado.competencia}\n"
                f"Número da guia: {numero}\n"
                f"Guia: {resultado.guia.status}\n"
                f"Relatório FGTS: {resultado.fgts.status}\n"
                f"Relatório Consignado: {resultado.consignado.status}\n\n"
                f"Arquivo da guia: {resultado.guia.caminho or '-'}\n\n"
                "O portal ficou pronto para a próxima guia."
            )
            messagebox.showinfo("Fase 5 concluída", mensagem)
            self._registrar(
                f"FASE 5 CONCLUÍDA: GUIA={resultado.guia.status}; FGTS={resultado.fgts.status}; "
                f"CONSIGNADO={resultado.consignado.status}; portal reiniciado."
            )

        except DownloadRelatorioTimeout as exc:
            self._registrar(f"DOWNLOAD NÃO CONCLUÍDO: {exc.tipo}.")
            continuar = messagebox.askyesno(
                "Relatório em PDF não concluído",
                "A guia já foi emitida, porém o download de um relatório em PDF não foi concluído "
                "dentro da janela de aproximadamente 5 segundos.\n\n"
                f"Relatório: {exc.tipo}\n\n"
                "SIM = continuar para a próxima guia (o portal tentará Reiniciar).\n"
                "NÃO = permanecer nesta guia para você conferir/tentar o download manualmente.\n\n"
                "Deseja continuar para a próxima guia?",
            )
            if continuar:
                try:
                    _reiniciar(sessao.page)
                    self._registrar(
                        f"Operador autorizou continuar apesar do download não concluído de {exc.tipo}. Portal reiniciado."
                    )
                    messagebox.showwarning(
                        "Guia emitida com pendência de relatório",
                        f"A guia foi emitida, mas o relatório {exc.tipo} ficou com status DOWNLOAD NÃO CONCLUÍDO.\n\n"
                        "O portal foi reiniciado e está pronto para a próxima guia.",
                    )
                except Exception as reinicio_exc:
                    raise PortalFlowError(
                        f"O relatório {exc.tipo} não concluiu e o portal também não pôde ser reiniciado: {reinicio_exc}"
                    ) from reinicio_exc
            else:
                self._registrar(
                    f"Operador optou por permanecer na guia após falha/atraso no download de {exc.tipo}."
                )
                messagebox.showinfo(
                    "Automação pausada nesta guia",
                    "A automação não clicou em Reiniciar.\n\n"
                    "Confira o relatório manualmente no portal. Depois poderemos retomar a partir daqui.",
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
            titulo = "Fase 5 interrompida" if isinstance(exc, PortalFlowError) else "Erro inesperado na Fase 5"
            messagebox.showerror(
                titulo,
                "A automação foi interrompida e NÃO continuará automaticamente.\n\n" + detalhe,
            )
            self._registrar(f"FASE 5 INTERROMPIDA: {exc}")
            if screenshot:
                self._registrar(f"Screenshot local do erro: {screenshot}")
        finally:
            sessao.fechar_conexao()
            self.browser_session = None
            self.btn_fase2.configure(state="normal")


def main() -> None:
    app = AppFGTSFase5()
    app.mainloop()


if __name__ == "__main__":
    main()
