from __future__ import annotations

import os
import threading
import tkinter as tk
import unicodedata
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from .app import AppFGTS
from .batch_state import carregar_controle, chave_item, registrar_guia_recuperada, salvar_status, status_atual
from .browser_connection import BrowserSession
from .phase3_flow import SemDebitos
from .phase5_flow import DownloadRelatorioTimeout, _reiniciar
from .phase6_flow import gerar_zip_competencia, pasta_competencia
from .portal_flow import salvar_screenshot_erro
from .production_flow import executar_item_producao


def _chave_ordenacao(coluna: str, valor: object):
    texto = str(valor or "").strip()
    if coluna in {"linha", "codigo"} and texto.isdecimal():
        return (0, int(texto))
    normalizado = unicodedata.normalize("NFKD", texto.casefold())
    return (1, "".join(ch for ch in normalizado if not unicodedata.combining(ch)))


class AppFGTSFinal(AppFGTS):
    def __init__(self) -> None:
        super().__init__()
        self.title("FGTS por Obra / Poligonal")
        self._configurar_colunas()
        self.tabela.configure(selectmode="extended")

        self.btn_preparar.configure(text="Conferir seleção", command=self._conferir_selecao)
        self.btn_fase2.configure(text="Gerar guias selecionadas", command=self._iniciar_lote)

        self._parar_apos_atual = threading.Event()
        self._executando = False

        barra_selecao = ttk.Frame(self.tabela.master, padding=(0, 6, 0, 0))
        barra_selecao.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Label(barra_selecao, text="Escolha algumas com Ctrl + clique, ou:").pack(side="left")
        self.btn_selecionar_pendentes = ttk.Button(
            barra_selecao, text="Selecionar todas as pendentes",
            command=self._selecionar_pendentes, state="disabled",
        )
        self.btn_selecionar_pendentes.pack(side="left", padx=8)
        self.btn_gerar_todas = ttk.Button(
            barra_selecao, text="Gerar todas as pendentes",
            command=self._gerar_todas_pendentes, state="disabled",
        )
        self.btn_gerar_todas.pack(side="left", padx=8)
        ttk.Button(barra_selecao, text="Limpar seleção", command=self._limpar_selecao).pack(side="left", padx=8)

        self.btn_atualizar = ttk.Button(
            self.acoes_adicionais, text="Atualizar situações", command=self._atualizar_situacoes,
        )
        self.btn_atualizar.pack(side="left", padx=8)

        self.btn_recuperada = ttk.Button(
            self.acoes_adicionais, text="Registrar guia recuperada", command=self._registrar_recuperada,
        )
        self.btn_recuperada.pack(side="left", padx=8)

        self.btn_parar = ttk.Button(
            self.acoes_adicionais,
            text="Parar após a atual",
            command=self._solicitar_parada,
            state="disabled",
        )
        self.btn_parar.pack(side="left", padx=8)

        self.btn_parar_agora = ttk.Button(
            self.acoes_adicionais,
            text="Parar imediatamente",
            command=self._parar_imediatamente,
            state="disabled",
        )
        self.btn_parar_agora.pack(side="left", padx=8)

        self.btn_zip = ttk.Button(
            self.acoes_adicionais,
            text="Gerar ZIP da competência",
            command=self._gerar_zip_manual,
            state="disabled",
        )
        self.btn_zip.pack(side="left", padx=8)

    def _configurar_colunas(self) -> None:
        # Tk limpa os títulos anteriores ao redefinir a lista de colunas.
        colunas = ("situacao", "linha", "codigo", "tipo", "inscricao", "servico", "tag")
        titulos = ("Situação da guia", "Linha", "Código", "Tipo", "Inscrição", "Serviço", "TAG")
        larguras = (250, 60, 90, 90, 150, 430, 220)
        self.tabela["columns"] = colunas
        self._titulos_colunas = dict(zip(colunas, titulos))
        self._ordenacao_coluna = None
        self._ordenacao_desc = False
        for coluna, titulo, largura in zip(colunas, titulos, larguras):
            self.tabela.heading(coluna, text=titulo, command=lambda c=coluna: self._ordenar_coluna(c))
            self.tabela.column(coluna, width=largura, anchor="w")

    def _ordenar_coluna(self, coluna: str) -> None:
        if self._executando:
            return
        descendente = not self._ordenacao_desc if self._ordenacao_coluna == coluna else False
        posicao = tuple(self.tabela["columns"]).index(coluna)
        linhas = list(self.tabela.get_children())
        linhas.sort(
            key=lambda iid: _chave_ordenacao(coluna, self.tabela.item(iid, "values")[posicao]),
            reverse=descendente,
        )
        for indice, iid in enumerate(linhas):
            self.tabela.move(iid, "", indice)
        self._ordenacao_coluna = coluna
        self._ordenacao_desc = descendente
        for nome, titulo in self._titulos_colunas.items():
            seta = " ▼" if descendente else " ▲"
            self.tabela.heading(nome, text=titulo + seta if nome == coluna else titulo)

    def _validar_planilha(self, caminho: Path) -> None:
        super()._validar_planilha(caminho)
        if self.resultado is not None and self.resultado.valida:
            self.btn_zip.configure(state="normal")
            self.status_var.set("Planilha validada. Selecione uma ou mais inscrições para gerar as guias.")
            self._atualizar_situacoes()
            self.btn_selecionar_pendentes.configure(state="normal")
            self.btn_gerar_todas.configure(state="normal")

    def _limpar_selecao(self) -> None:
        if self._executando:
            return
        self.tabela.selection_remove(*self.tabela.selection())

    def _selecionar_pendentes(self) -> int:
        if self._executando or self.resultado is None or not self.resultado.valida:
            return 0
        dados = carregar_controle(self.resultado.competencia)
        linhas = [
            str(item.linha) for item in self.resultado.itens
            if not dados.get(chave_item(self.resultado.competencia, item.tipo_inscricao, item.inscricao), {}).get("status")
            and self.tabela.exists(str(item.linha))
        ]
        self.tabela.selection_remove(*self.tabela.selection())
        if not linhas:
            messagebox.showinfo("Seleção em massa", "Não há inscrições sem processamento registrado para selecionar.")
            return 0
        self.tabela.selection_set(*linhas)
        self.tabela.focus(linhas[0])
        self.tabela.see(linhas[0])
        self.status_var.set(f"{len(linhas)} inscrição(ões) pendente(s) selecionada(s). Confira antes de gerar.")
        return len(linhas)

    def _gerar_todas_pendentes(self) -> None:
        if self._selecionar_pendentes():
            self._iniciar_lote()

    def _atualizar_situacoes(self) -> None:
        if self.resultado is None or not self.resultado.valida:
            return
        dados = carregar_controle(self.resultado.competencia)
        for item in self.resultado.itens:
            registro = dados.get(chave_item(self.resultado.competencia, item.tipo_inscricao, item.inscricao), {})
            status = registro.get("status")
            guia = registro.get("guia")
            guia_baixada = bool(guia and Path(guia).is_file())
            fgts = registro.get("fgts")
            fgts_baixado = bool(fgts and Path(fgts).is_file())
            if status == "CONCLUIDO":
                situacao = "Concluída" if guia_baixada and fgts_baixado else "Concluída; conferir arquivos"
            elif status == "GUIA_RECUPERADA":
                situacao = "Guia recuperada; relatórios pendentes"
            elif status == "CONFERIR_EMISSAO":
                situacao = "Conferir emissão; NÃO repetir"
            elif status in {"PENDENTE_RELATORIO", "PENDENTE_RELATORIO_CONTINUADO"}:
                situacao = "Emitida; relatório pendente"
            elif status == "SEM_DEBITOS":
                situacao = "Não há débitos"
            elif status == "PROCESSANDO":
                situacao = "Em processamento; conferir se parou"
            elif status == "ERRO":
                situacao = "Erro; verificar antes de repetir"
            else:
                situacao = "Pendente"
            if guia_baixada:
                situacao += " | PDF da guia: sim"
            if fgts_baixado:
                situacao += " | Relatório: sim"
            linha = str(item.linha)
            if self.tabela.exists(linha):
                self.tabela.item(linha, values=(situacao, item.linha, item.codigo, item.tipo_inscricao,
                                                item.inscricao, item.servico, item.tag))

    def _registrar_recuperada(self) -> None:
        itens = self._itens_selecionados()
        if len(itens) != 1 or self.resultado is None:
            messagebox.showwarning("Registrar guia", "Selecione uma única inscrição.")
            return
        item = itens[0]
        atual = status_atual(self.resultado.competencia, item.tipo_inscricao, item.inscricao)
        if atual == "CONCLUIDO":
            messagebox.showinfo("Registrar guia", "Esta inscrição já está concluída.")
            return
        pdf = filedialog.askopenfilename(title="Selecione o PDF da guia recuperada", filetypes=[("PDF", "*.pdf")])
        if not pdf:
            return
        numero = simpledialog.askstring("Número da guia", "Número da guia (deixe vazio se não souber):", parent=self)
        if numero is None:
            return
        if not messagebox.askyesno("Confirmar registro", f"Registrar guia recuperada para {item.tipo_inscricao} {item.inscricao}?\n\n{pdf}\n\nIsso não marcará os relatórios como baixados nem o lote como concluído."):
            return
        try:
            registrar_guia_recuperada(self.resultado.competencia, item.tipo_inscricao, item.inscricao,
                                      numero_guia=numero.strip() or None, guia=pdf)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Registrar guia", str(exc))
            return
        self._atualizar_situacoes()
        self._registrar(f"Guia recuperada registrada para {item.tipo_inscricao} {item.inscricao}.")

    def _itens_selecionados(self):
        if self.resultado is None:
            return []
        por_linha = {str(item.linha): item for item in self.resultado.itens}
        selecionados = set(self.tabela.selection())
        return [por_linha[iid] for iid in self.tabela.get_children()
                if iid in selecionados and iid in por_linha]

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

    def _parar_imediatamente(self) -> None:
        if not self._executando:
            return
        # Encerra somente este processo Python. O Chrome dedicado permanece aberto.
        # O checkpoint PROCESSANDO exige conferência no portal antes de repetir a inscrição.
        os._exit(130)

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
            if status_atual(self.resultado.competencia, item.tipo_inscricao, item.inscricao) in {"CONCLUIDO", "CONFERIR_EMISSAO", "GUIA_RECUPERADA", "PROCESSANDO", "PENDENTE_RELATORIO", "PENDENTE_RELATORIO_CONTINUADO"}
        ]
        pendentes = [item for item in itens if item not in concluidos]
        if not pendentes:
            messagebox.showinfo("Processamento", "As inscrições selecionadas já foram concluídas ou exigem conferência antes de nova emissão.")
            return

        linhas = "\n".join(
            f"• {item.tipo_inscricao} {item.inscricao} | {item.codigo} - {item.servico}"
            for item in pendentes
        )
        complemento = ""
        if concluidos:
            complemento = f"\n\n{len(concluidos)} inscrição(ões) concluída(s) ou em conferência será(ão) ignorada(s)."

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
        self.btn_parar_agora.configure(state="normal")
        self.btn_chrome.configure(state="disabled")
        self.btn_preparar.configure(state="disabled")
        self.btn_zip.configure(state="disabled")
        self.btn_selecionar_pendentes.configure(state="disabled")
        self.btn_gerar_todas.configure(state="disabled")
        threading.Thread(target=self._worker_lote, args=(pendentes,), daemon=True).start()

    def _worker_lote(self, itens) -> None:
        sessao = BrowserSession()
        concluidos = 0
        pendencias = 0
        erros = 0
        sem_debitos = 0
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

                except SemDebitos as exc:
                    sem_debitos += 1
                    self._log_worker(f"[{indice}/{total}] NÃO HÁ DÉBITOS | {item.tipo_inscricao} {item.inscricao}")

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
                    self._log_worker(f"[{indice}/{total}] Interrompido: {detalhe}")
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

                self.after(0, self._atualizar_situacoes)

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
                f"Concluídas: {concluidos}\nSem débitos: {sem_debitos}\nPendências de relatório: {pendencias}\nErros: {erros}\n\n"
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
                self.btn_parar_agora.configure(state="disabled")
                self.btn_chrome.configure(state="normal")
                self.btn_preparar.configure(state="normal")
                self.btn_zip.configure(state="normal")
                self.btn_selecionar_pendentes.configure(state="normal")
                self.btn_gerar_todas.configure(state="normal")
                self._atualizar_situacoes()
            self.after(0, liberar)


def main() -> None:
    app = AppFGTSFinal()
    app.mainloop()


if __name__ == "__main__":
    main()
