from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .app import AppFGTS
from .batch_state import salvar_status, status_atual
from .browser_connection import BrowserSession
from .phase5_flow import DownloadRelatorioTimeout, _reiniciar
from .phase6_flow import achatar_downloads, executar_item_lote
from .portal_flow import salvar_screenshot_erro


class AppFGTSFase6(AppFGTS):
    def __init__(self) -> None:
        super().__init__()
        self.title("FGTS por Obra/Poligonal — Fase 6 Lote Controlado")
        self.tabela.configure(selectmode="extended")

        self.btn_fase2.configure(
            text="FASE 6 — Processar selecionadas",
            command=self._iniciar_lote,
        )
        self.btn_preparar.configure(text="Conferir seleção", command=self._conferir_selecao)

        self._parar_apos_atual = threading.Event()
        self._executando = False

        self.btn_parar = ttk.Button(
            self.btn_fase2.master,
            text="Parar após a atual",
            command=self._solicitar_parada,
            state="disabled",
        )
        self.btn_parar.pack(side="left", padx=8)

    def _itens_selecionados(self):
        if self.resultado is None:
            return []
        linhas = {int(iid) for iid in self.tabela.selection()}
        return [item for item in self.resultado.itens if item.linha in linhas]

    def _conferir_selecao(self) -> None:
        itens = self._itens_selecionados()
        if not itens:
            messagebox.showwarning("Seleção", "Selecione uma ou mais inscrições com Ctrl + clique.")
            return
        texto = "\n".join(
            f"Linha {item.linha}: {item.tipo_inscricao} {item.inscricao} | {item.codigo} - {item.servico}"
            for item in itens
        )
        messagebox.showinfo(
            "Inscrições selecionadas",
            f"Quantidade selecionada: {len(itens)}\n\n{texto}",
        )

    def _solicitar_parada(self) -> None:
        if not self._executando:
            return
        self._parar_apos_atual.set()
        self._registrar("PARADA SOLICITADA: o lote será interrompido após concluir a inscrição atual.")

    def _log_worker(self, mensagem: str) -> None:
        self.after(0, lambda m=mensagem: self._registrar(m))

    def _perguntar_worker(self, titulo: str, mensagem: str) -> bool:
        evento = threading.Event()
        resposta = {"valor": False}

        def perguntar() -> None:
            resposta["valor"] = messagebox.askyesno(titulo, mensagem)
            evento.set()

        self.after(0, perguntar)
        evento.wait()
        return resposta["valor"]

    def _mostrar_worker(self, tipo: str, titulo: str, mensagem: str) -> None:
        def mostrar() -> None:
            if tipo == "erro":
                messagebox.showerror(titulo, mensagem)
            elif tipo == "aviso":
                messagebox.showwarning(titulo, mensagem)
            else:
                messagebox.showinfo(titulo, mensagem)

        self.after(0, mostrar)

    def _iniciar_lote(self) -> None:
        if self._executando:
            return
        if self.resultado is None or not self.resultado.valida:
            return

        itens = self._itens_selecionados()
        if not itens:
            messagebox.showwarning(
                "Seleção do lote",
                "Selecione as inscrições que ainda faltam usando Ctrl + clique.",
            )
            return

        ja_concluidos = [
            item
            for item in itens
            if status_atual(self.resultado.competencia, item.tipo_inscricao, item.inscricao) == "CONCLUIDO"
        ]
        pendentes = [item for item in itens if item not in ja_concluidos]

        if not pendentes:
            messagebox.showinfo(
                "Lote",
                "Todas as inscrições selecionadas já constam como CONCLUÍDAS no checkpoint local.",
            )
            return

        linhas = "\n".join(
            f"• {item.tipo_inscricao} {item.inscricao} | {item.codigo} - {item.servico}"
            for item in pendentes
        )
        if ja_concluidos:
            linhas += f"\n\n{len(ja_concluidos)} inscrição(ões) já concluída(s) será(ão) ignorada(s)."

        confirmar = messagebox.askyesno(
            "Confirmar lote real",
            f"ATENÇÃO: serão emitidas guias reais para {len(pendentes)} inscrição(ões).\n\n"
            f"Competência: {self.resultado.competencia}\n\n{linhas}\n\n"
            "Deseja iniciar o lote?",
        )
        if not confirmar:
            return

        self._executando = True
        self._parar_apos_atual.clear()
        self.btn_fase2.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.btn_chrome.configure(state="disabled")
        self.btn_preparar.configure(state="disabled")

        thread = threading.Thread(target=self._worker_lote, args=(pendentes,), daemon=True)
        thread.start()

    def _worker_lote(self, itens) -> None:
        sessao = BrowserSession()
        concluidos = 0
        pendencias = 0
        erros = 0
        interrompido = False

        try:
            self._log_worker("FASE 6 INICIADA — conectando ao Chrome dedicado...")
            info = sessao.conectar()
            self._log_worker(f"Chrome conectado: {info.titulo} | {info.url}")

            total = len(itens)
            for indice, item in enumerate(itens, start=1):
                if self._parar_apos_atual.is_set() and indice > 1:
                    interrompido = True
                    break

                self._log_worker(
                    f"===== LOTE {indice}/{total} | {item.tipo_inscricao} {item.inscricao} | "
                    f"{item.codigo} - {item.servico} ====="
                )

                try:
                    resultado = executar_item_lote(
                        sessao.page,
                        item=item,
                        competencia=self.resultado.competencia,
                        vencimento=self.resultado.vencimento_calculado,
                        log=self._log_worker,
                    )
                    concluidos += 1
                    self._log_worker(
                        f"LOTE {indice}/{total} CONCLUÍDO | Guia {resultado.numero_guia or 'número não identificado'}"
                    )

                except DownloadRelatorioTimeout as exc:
                    pendencias += 1
                    try:
                        achatar_downloads(self.resultado.competencia, item.inscricao, item.tag)
                    except Exception:
                        pass
                    salvar_status(
                        self.resultado.competencia,
                        item.tipo_inscricao,
                        item.inscricao,
                        status="PENDENTE_RELATORIO",
                        erro=str(exc),
                    )

                    continuar = self._perguntar_worker(
                        "Relatório não concluído",
                        f"A guia de {item.tipo_inscricao} {item.inscricao} já foi emitida, mas o relatório "
                        f"{exc.tipo} não concluiu no tempo esperado.\n\n"
                        "SIM = Reiniciar e continuar para a próxima inscrição.\n"
                        "NÃO = parar o lote nesta guia para conferência manual.\n\n"
                        "Deseja continuar?",
                    )
                    if continuar:
                        _reiniciar(sessao.page)
                        salvar_status(
                            self.resultado.competencia,
                            item.tipo_inscricao,
                            item.inscricao,
                            status="PENDENTE_RELATORIO_CONTINUADO",
                            erro=str(exc),
                        )
                        self._log_worker("Operador autorizou continuar com pendência de relatório.")
                    else:
                        interrompido = True
                        break

                except Exception as exc:
                    erros += 1
                    screenshot = None
                    try:
                        screenshot = salvar_screenshot_erro(sessao.page, Path.cwd())
                    except Exception:
                        pass
                    detalhe = str(exc)
                    if screenshot:
                        detalhe += f"\nScreenshot: {screenshot}"
                    self._mostrar_worker(
                        "erro",
                        "Lote interrompido",
                        f"Erro em {item.tipo_inscricao} {item.inscricao}.\n\n{detalhe}\n\n"
                        "O lote foi interrompido para evitar avançar às cegas.",
                    )
                    interrompido = True
                    break

                if self._parar_apos_atual.is_set():
                    interrompido = True
                    break

        except Exception as exc:
            erros += 1
            self._mostrar_worker("erro", "Fase 6", f"Não foi possível iniciar/continuar o lote.\n\n{exc}")
        finally:
            try:
                sessao.fechar_conexao()
            except Exception:
                pass

            checkpoint = (
                Path.home()
                / "Downloads"
                / "FGTS_por_obra_poligonal"
                / self.resultado.competencia.replace("/", "-")
                / "controle_lote.json"
            )
            resumo = (
                f"Lote {'INTERROMPIDO' if interrompido else 'FINALIZADO'}\n\n"
                f"Concluídas: {concluidos}\n"
                f"Pendências de relatório: {pendencias}\n"
                f"Erros: {erros}\n\n"
                f"Checkpoint: {checkpoint}"
            )
            self._log_worker(resumo.replace("\n", " | "))
            self._mostrar_worker("info" if not erros else "aviso", "Resumo do lote", resumo)

            def liberar() -> None:
                self._executando = False
                self.btn_fase2.configure(state="normal")
                self.btn_parar.configure(state="disabled")
                self.btn_chrome.configure(state="normal")
                self.btn_preparar.configure(state="normal")

            self.after(0, liberar)


def main() -> None:
    app = AppFGTSFase6()
    app.mainloop()


if __name__ == "__main__":
    main()
