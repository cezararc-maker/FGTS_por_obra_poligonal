from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .browser_connection import BrowserSession
from .excel_reader import ler_planilha
from .models import ResultadoPlanilha


class AppFGTS(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("FGTS por Obra/Poligonal — Modo TESTE Fase 1")
        self.geometry("1180x720")
        self.minsize(980, 620)

        self.resultado: ResultadoPlanilha | None = None
        self.browser_session: BrowserSession | None = None

        self.caminho_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Selecione a planilha para iniciar.")
        self.resumo_var = tk.StringVar(value="Nenhuma planilha validada.")

        self._montar_interface()

    def _montar_interface(self) -> None:
        topo = ttk.Frame(self, padding=10)
        topo.pack(fill="x")

        ttk.Label(topo, text="Planilha:").grid(row=0, column=0, sticky="w")
        ttk.Entry(topo, textvariable=self.caminho_var, width=90, state="readonly").grid(
            row=0, column=1, padx=8, sticky="ew"
        )
        ttk.Button(topo, text="Selecionar Excel", command=self._selecionar_planilha).grid(row=0, column=2)
        topo.columnconfigure(1, weight=1)

        resumo = ttk.LabelFrame(self, text="Resumo da validação", padding=10)
        resumo.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(resumo, textvariable=self.resumo_var, justify="left").pack(anchor="w")

        tabela_frame = ttk.LabelFrame(self, text="Inscrições disponíveis para teste", padding=8)
        tabela_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        colunas = ("linha", "codigo", "tipo", "inscricao", "servico", "tag")
        self.tabela = ttk.Treeview(tabela_frame, columns=colunas, show="headings", selectmode="browse")
        titulos = {
            "linha": "Linha",
            "codigo": "Código",
            "tipo": "Tipo",
            "inscricao": "Inscrição",
            "servico": "Serviço",
            "tag": "TAG",
        }
        larguras = {"linha": 60, "codigo": 90, "tipo": 90, "inscricao": 150, "servico": 430, "tag": 220}
        for coluna in colunas:
            self.tabela.heading(coluna, text=titulos[coluna])
            self.tabela.column(coluna, width=larguras[coluna], anchor="w")

        scroll_y = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll_y.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        acoes = ttk.Frame(self, padding=(10, 0, 10, 10))
        acoes.pack(fill="x")

        self.btn_preparar = ttk.Button(
            acoes,
            text="Preparar teste de 1 inscrição",
            command=self._preparar_teste,
            state="disabled",
        )
        self.btn_preparar.pack(side="left")

        self.btn_chrome = ttk.Button(
            acoes,
            text="Testar conexão com Chrome",
            command=self._testar_chrome,
            state="disabled",
        )
        self.btn_chrome.pack(side="left", padx=8)

        ttk.Label(acoes, textvariable=self.status_var).pack(side="left", padx=12)

        log_frame = ttk.LabelFrame(self, text="Log do teste", padding=8)
        log_frame.pack(fill="both", padx=10, pady=(0, 10))
        self.log = tk.Text(log_frame, height=8, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)

    def _registrar(self, mensagem: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", mensagem + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.status_var.set(mensagem)
        self.update_idletasks()

    def _selecionar_planilha(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecione a planilha do FGTS",
            filetypes=[("Planilha Excel", "*.xlsx")],
        )
        if not caminho:
            return

        self.caminho_var.set(caminho)
        self._validar_planilha(Path(caminho))

    def _validar_planilha(self, caminho: Path) -> None:
        self._limpar_tabela()
        self.btn_preparar.configure(state="disabled")
        self.btn_chrome.configure(state="disabled")
        self._registrar(f"Validando planilha: {caminho.name}")

        try:
            resultado = ler_planilha(caminho)
        except Exception as exc:  # proteção da interface para erros inesperados de arquivo
            self.resultado = None
            messagebox.showerror("Erro ao ler planilha", str(exc))
            self._registrar(f"ERRO: {exc}")
            return

        self.resultado = resultado

        if resultado.erros:
            detalhes = "\n".join(f"• {erro}" for erro in resultado.erros)
            self.resumo_var.set(
                f"Competência: {resultado.competencia or '-'}\n"
                f"Erros encontrados: {len(resultado.erros)}"
            )
            messagebox.showerror("Planilha inválida", detalhes)
            self._registrar(f"Validação bloqueada: {len(resultado.erros)} erro(s).")
            return

        for item in resultado.itens:
            self.tabela.insert(
                "",
                "end",
                iid=str(item.linha),
                values=(item.linha, item.codigo, item.tipo_inscricao, item.inscricao, item.servico, item.tag),
            )

        venc_calc = resultado.vencimento_calculado.strftime("%d/%m/%Y")
        venc_planilha = (
            resultado.vencimento_conferencia.strftime("%d/%m/%Y")
            if resultado.vencimento_conferencia
            else "não informado"
        )

        qtd_cnpj = sum(1 for item in resultado.itens if item.tipo_inscricao == "CNPJ")
        qtd_cno = sum(1 for item in resultado.itens if item.tipo_inscricao == "CNO")
        texto = (
            f"Competência: {resultado.competencia}\n"
            f"Vencimento calculado: {venc_calc}\n"
            f"Vencimento da planilha (conferência): {venc_planilha}\n"
            f"Registros válidos: {len(resultado.itens)} — CNPJ: {qtd_cnpj} | CNO: {qtd_cno}"
        )
        if resultado.avisos:
            texto += "\nAvisos: " + " | ".join(resultado.avisos)
        self.resumo_var.set(texto)

        if resultado.itens:
            primeiro = str(resultado.itens[0].linha)
            self.tabela.selection_set(primeiro)
            self.tabela.focus(primeiro)

        self.btn_preparar.configure(state="normal")
        self.btn_chrome.configure(state="normal")
        self._registrar(f"Planilha validada com sucesso: {len(resultado.itens)} registro(s).")

    def _limpar_tabela(self) -> None:
        for item in self.tabela.get_children():
            self.tabela.delete(item)

    def _item_selecionado(self):
        if self.resultado is None:
            return None
        selecionados = self.tabela.selection()
        if not selecionados:
            return None
        linha = int(selecionados[0])
        return next((item for item in self.resultado.itens if item.linha == linha), None)

    def _preparar_teste(self) -> None:
        if self.resultado is None or not self.resultado.valida:
            return

        item = self._item_selecionado()
        if item is None:
            messagebox.showwarning("Seleção", "Selecione uma inscrição na tabela.")
            return

        resumo = (
            "MODO TESTE — NENHUMA GUIA SERÁ EMITIDA NESTA FASE\n\n"
            f"Tipo: {item.tipo_inscricao}\n"
            f"Inscrição: {item.inscricao}\n"
            f"Código: {item.codigo}\n"
            f"Serviço: {item.servico}\n"
            f"TAG: {item.tag}\n"
            f"Competência: {self.resultado.competencia}\n"
            f"Vencimento calculado: {self.resultado.vencimento_calculado:%d/%m/%Y}\n\n"
            "Próximo passo do teste: conectar ao Chrome visível e somente confirmar que a sessão pode ser lida."
        )
        messagebox.showinfo("Inscrição preparada para teste", resumo)
        self._registrar(
            f"Teste preparado: linha {item.linha}, {item.tipo_inscricao} {item.inscricao}, TAG '{item.tag}'."
        )

    def _testar_chrome(self) -> None:
        self._registrar("Tentando conectar ao Chrome dedicado em 127.0.0.1:9222...")
        sessao = BrowserSession()
        try:
            info = sessao.conectar()
        except Exception as exc:
            sessao.fechar_conexao()
            messagebox.showerror(
                "Chrome não conectado",
                "Não foi possível conectar ao Chrome dedicado.\n\n"
                "Execute primeiro scripts\\abrir_chrome_teste.bat, faça o login manual no portal "
                "e tente novamente.\n\n"
                f"Detalhe técnico: {exc}",
            )
            self._registrar(f"Falha de conexão com Chrome: {exc}")
            return

        self.browser_session = sessao
        mensagem = (
            "Conexão com Chrome realizada com sucesso.\n\n"
            f"Páginas abertas: {info.paginas_abertas}\n"
            f"Título atual: {info.titulo}\n"
            f"URL atual: {info.url}\n\n"
            "Nenhum clique ou alteração foi executado pelo programa."
        )
        messagebox.showinfo("Chrome conectado", mensagem)
        self._registrar(f"Chrome conectado. Página atual: {info.titulo or '(sem título)'}")
        sessao.fechar_conexao()
        self.browser_session = None


def main() -> None:
    app = AppFGTS()
    app.mainloop()


if __name__ == "__main__":
    main()
