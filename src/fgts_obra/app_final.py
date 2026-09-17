from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .app import AppFGTS
from .batch_state import salvar_status, status_atual
from .browser_connection import BrowserSession
from .phase5_flow import DownloadRelatorioTimeout, _reiniciar
from .phase6_flow import gerar_zip_competencia, pasta_competencia
from .portal_flow import salvar_screenshot_erro
from .production_flow import executar_item_producao


class AppFGTSFinal(AppFGTS):
    def __init__(self) -> None:
        super().__init__()
        self.title("FGTS por Obra / Poligonal")
        self.tabela.configure(selectmode="extended")

        self.btn_preparar.configure(text="Conferir seleção", command=self._conferir_selecao)
        self.btn_fase2.configure(text="Gerar guias selecionadas", command=self._iniciar_lote)

        self._parar_apos_atual = threading.Event()
        self._executando = False

        self.btn_parar = ttk.Button(
            self.btn_fase2.master,
            text="Parar após a atual",
            command=self._solicitar_parada,
            state="disabled",
        )
        self.btn_parar.pack(side="left", padx=8)

        self.btn_zip = ttk.Button(
            self.btn_fase2.master,
            text="Gerar ZIP da competência",
            command=self._gerar_zip_manual,
            state="disabled",
        )
        self.btn_zip.pack(side="left", padx=8)

    def _validar_planilha(self, caminho: Path) -> None:
        super()._validar_planilha(caminho)
        if self.resultado is not None and self.resultado.valida:
            self.btn_zip.configure(state="normal")
            self.status_var.set("Planilha validada. Selecione uma ou mais inscrições para gerar as guias.")

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
        messagebox.showinfo("Inscrições selecionadas", f"Quantidade: {len(itens)}\n\n{texto}")

    def _solicitar_parada(self) -> None:
        if self._executando:
            self._parar_apos_atual.set()
            self._registrar("Parada solicitada: o lote será encerrado após a inscrição atual.")

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

    def _gerar_zip_manual(self) -> None:
        if self.resultado is None or not self.resultado.valida:
            return
        try:
            caminho = gerar_zip_competencia(self.resultado.competencia)
        except Exception as exc:
            messagebox.showerror("Gerar ZIP", str(exc))
            self._registrar(f"Falha ao gerar ZIP: {exc}")
            return
        self._registrar(f"ZIP da competência criado: {caminho}")
        messagebox.showinfo("ZIP criado", f"Arquivo criado com sucesso:\n\n{caminho}")

    def _todos_concluidos(self) -> bool:
        if self.resultado is None:
            return False
        return all(
            status_atual(self.resultado.competencia, item.tipo_inscricao, item.inscricao) == "CONCLUIDO"
            for item in self.resultado.itens
        )

    def _iniciar_lote(self) -> None:
        if self._executando or self.resultado is None or not self.resultado.valida:
            return
        itens = self._itens_selecionados()
        if not itens:
            messagebox.showwarning("Seleção", "Selecione uma ou mais inscrições para processar.")
            return

        concluidos = [
            item for item in itens
            if status_atual(self.resultado.competencia, item.tipo_inscricao, item.inscricao) == "CONCLUIDO"
        ]
        pendentes = [item for item in itens if item not in concluidos]
        if not pendentes:
            messagebox.showinfo("Processamento", "Todas as inscrições selecionadas já estão concluídas no checkpoint.")
            return

        linhas = "\n".join(
            f"• {item.tipo_inscricao} {item.inscricao} | {item.codigo} - {item.servico}"
            for item in pendentes
        )
        complemento = ""
        if concluidos:
            complemento = f"\n\n{len(concluidos)} inscrição(ões) já concluída(s) será(ão) ignorada(s)."

        if not messagebox.askyesno(
            "Confirmar geração",
            f"Serão emitidas guias reais para {len(pendentes)} inscrição(ões).\n\n"
            f"Competência: {self.resultado.competencia}\n\n{linhas}{complemento}\n\n"
            "Deseja iniciar?",
        ):
            return

        self._executando = True
        self._parar_apos_atual.clear()
        self.btn_fase2.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.btn_chrome.configure(state="disabled")
        self.btn_preparar.configure(state="disabled")
        self.btn_zip.configure(state="disabled")
        threading.Thread(target=self._worker_lote, args=(pendentes,), daemon=True).start()

    def _worker_lote(self, itens) -> None:
        sessao = BrowserSession()
        concluidos = 0
        pendencias = 0
        erros = 0
        interrompido = False

        try:
            self._log_worker("Conectando ao Chrome dedicado...")
            info = sessao.conectar()
            self._log_worker(f"Chrome conectado: {info.titulo} | {info.url}")
            total = len(itens)

            for indice, item in enumerate(itens, start=1):
                if self._parar_apos_atual.is_set() and indice > 1:
                    interrompido = True
                    break

                self._log_worker(
                    f"===== {indice}/{total} | {item.tipo_inscricao} {item.inscricao} | {item.codigo} - {item.servico} ====="
                )
                try:
                    resultado = executar_item_producao(
                        sessao.page,
                        item=item,
                        competencia=self.resultado.competencia,
                        vencimento=self.resultado.vencimento_calculado,
                        log=self._log_worker,
                        indice=indice,
                        total=total,
                    )
                    concluidos += 1
                    self._log_worker(
                        f"[{indice}/{total}] CONCLUÍDO | Guia {resultado.numero_guia or 'número não identificado'} | "
                        f"Pasta: {Path(resultado.guia.caminho).parent if resultado.guia.caminho else '-'}"
                    )

                except DownloadRelatorioTimeout as exc:
                    pendencias += 1
                    salvar_status(
                        self.resultado.competencia,
                        item.tipo_inscricao,
                        item.inscricao,
                        status="PENDENTE_RELATORIO",
                        erro=str(exc),
                    )
                    continuar = self._perguntar_worker(
                        "Relatório não concluído",
                        f"A guia de {item.tipo_inscricao} {item.inscricao} foi emitida, mas o relatório {exc.tipo} "
                        "não concluiu no tempo esperado.\n\nSIM = reiniciar e continuar.\nNÃO = permanecer nesta guia.",
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
                        "Processamento interrompido",
                        f"Erro em {item.tipo_inscricao} {item.inscricao}.\n\n{detalhe}\n\n"
                        "O lote foi interrompido para evitar continuar em estado incerto.",
                    )
                    interrompido = True
                    break

                if self._parar_apos_atual.is_set():
                    interrompido = True
                    break
        except Exception as exc:
            erros += 1
            self._mostrar_worker("erro", "FGTS por Obra", f"Não foi possível iniciar/continuar o lote.\n\n{exc}")
        finally:
            try:
                sessao.fechar_conexao()
            except Exception:
                pass

            zip_criado = None
            if not interrompido and erros == 0 and pendencias == 0 and self._todos_concluidos():
                try:
                    zip_criado = gerar_zip_competencia(self.resultado.competencia)
                    self._log_worker(f"ZIP da competência criado: {zip_criado}")
                except Exception as exc:
                    self._log_worker(f"Aviso: as guias terminaram, mas o ZIP não pôde ser criado automaticamente: {exc}")

            pasta = pasta_competencia(self.resultado.competencia)
            resumo = (
                f"Processamento {'INTERROMPIDO' if interrompido else 'FINALIZADO'}\n\n"
                f"Concluídas: {concluidos}\nPendências de relatório: {pendencias}\nErros: {erros}\n\n"
                f"Pasta da competência: {pasta}"
            )
            if zip_criado:
                resumo += f"\nZIP: {zip_criado}"
            self._log_worker(resumo.replace("\n", " | "))
            self._mostrar_worker("info" if erros == 0 else "aviso", "Resumo", resumo)

            def liberar() -> None:
                self._executando = False
                self.btn_fase2.configure(state="normal")
                self.btn_parar.configure(state="disabled")
                self.btn_chrome.configure(state="normal")
                self.btn_preparar.configure(state="normal")
                self.btn_zip.configure(state="normal")
            self.after(0, liberar)


def main() -> None:
    app = AppFGTSFinal()
    app.mainloop()


if __name__ == "__main__":
    main()
