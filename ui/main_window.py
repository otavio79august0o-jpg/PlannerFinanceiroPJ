"""
Main window for the Planner Empresarial PJ application.

This module defines the MainWindow class, which provides a top bar
displaying the current user, company and login time, along with a
sidebar navigation that allows switching between different pages of the
application. The pages include dashboard, profile, management views
for categories, accounts and budgets, as well as placeholders for
recorrentes, folhas de pagamento and other features yet to be
implemented. Each management view is instantiated with the current
company code so that data is scoped correctly.

The sidebar uses a QListWidget to list page names; when the user
selects an item, the corresponding page widget is displayed in the
central stacked widget. The structure allows new pages to be added
easily by appending to the ``_menu_items`` list in ``_build_ui``.

Usage:
    main_win = MainWindow(codigoempresa="EMPRESA_XYZ", usuario={"username": "admin"})
    main_win.show()

Note: This file assumes that the following modules exist within the
``ui`` package: ``categories_view``, ``accounts_view`` and
``orcamentos_view``. If additional pages are implemented, import and
instantiate their classes as needed.
"""

from __future__ import annotations

import datetime
from typing import Optional, List, Tuple

from PyQt5 import QtWidgets, QtGui, QtCore

from .categories_view import CategoriesView
from .accounts_view import AccountsView
from .orcamentos_view import OrcamentosView
# Import real view widgets for Financeiro and Recorrentes
from .transactions_view import TransactionsView
from .recorrentes_view import RecorrentesView


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window with a top bar and sidebar navigation.

    Parameters
    ----------
    codigoempresa: str
        Identifier of the company whose data is being displayed.
    usuario: dict
        Dictionary representing the authenticated user. Should contain
        at least the key ``username`` for display in the top bar.
    """

    def __init__(self, codigoempresa: str, usuario: dict) -> None:
        super().__init__()
        self.codigoempresa = codigoempresa
        self.usuario = usuario or {}
        self.login_dt = datetime.datetime.now()
        # Tema atual: padrão escuro
        self._current_theme = "dark"

        # Build and set up the UI
        self._setup_window()
        self._build_ui()

    # ------------------------------------------------------------------
    # Window and UI construction
    # ------------------------------------------------------------------
    def _setup_window(self) -> None:
        """Basic window configuration."""
        self.setWindowTitle("Planner Empresarial PJ")
        self.resize(1280, 720)
        # Set an application icon if desired (requires an icon file in ui/icons).
        try:
            # Usa o caminho correto com caixa alta conforme nome do arquivo na pasta ``icons``
            icon = QtGui.QIcon("ui/icons/MF.png")
            if not icon.isNull():
                self.setWindowIcon(icon)
        except Exception:
            pass

    def _build_ui(self) -> None:
        """Construct the top bar, sidebar and central stacked widget."""
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Build top bar
        top_bar = self._create_top_bar()
        root_layout.addWidget(top_bar)

        # Build content area with sidebar and stack
        content_frame = QtWidgets.QFrame()
        content_layout = QtWidgets.QHBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar list
        self.sidebar = QtWidgets.QListWidget()
        self.sidebar.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.sidebar.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Do not set a fixed style here; styles will be applied via QSS in the theme

        # Stacked widget for pages
        self.stack = QtWidgets.QStackedWidget()

        # Agrupa sidebar em um contêiner vertical
        side_container = QtWidgets.QFrame()
        # Nomeamos a barra lateral para que estilos em QSS (QFrame#Sidebar) sejam aplicados
        side_container.setObjectName("Sidebar")
        # Aumenta a largura da barra lateral para melhor proporção
        side_container.setFixedWidth(260)
        # Permitir que a barra lateral ocupe toda a altura
        side_container.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding
        )
        side_layout = QtWidgets.QVBoxLayout(side_container)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        # Adiciona a lista diretamente; sem stretch para que a barra ocupe toda a altura
        side_layout.addWidget(self.sidebar)

        # Adiciona contêiner lateral e área central ao layout
        content_layout.addWidget(side_container)
        content_layout.addWidget(self.stack)
        # Define fatores de estiramento para que a área de páginas ocupe o restante do espaço horizontal
        content_layout.setStretchFactor(side_container, 0)
        content_layout.setStretchFactor(self.stack, 1)
        # Por fim adiciona o content_frame ao layout raiz
        root_layout.addWidget(content_frame)

        # Populate the sidebar and stack with pages
        self._populate_pages()
        # Connect selection change to stack index change
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)

        # Set default page to first one
        if self.sidebar.count() > 0:
            self.sidebar.setCurrentRow(0)

    def _create_top_bar(self) -> QtWidgets.QWidget:
        """
        Create the top bar with application title and session information.

        The bar displays the username, company identifier and login
        timestamp. Styling is kept simple; background colouring is handled
        via inline CSS on the bar.
        """
        top_bar = QtWidgets.QFrame()
        # Definimos o nome do objeto como "TopBar" para que as regras
        # de QSS em dark.qss/light.qss se apliquem corretamente (QFrame#TopBar)
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(50)
        top_layout = QtWidgets.QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)
        top_layout.setSpacing(12)

        # Title label
        title_label = QtWidgets.QLabel("MF Financier PJ")
        # Nomeamos para aplicar estilos específicos (QLabel#TopBarTitle)
        title_label.setObjectName("TopBarTitle")
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #e5e7eb;"
        )

        # Spacer
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )

        # Session info
        username = self.usuario.get("username") or self.usuario.get("login") or "Usuário"
        session_text = (
            f"Usuário: {username} | Empresa: {self.codigoempresa} | Login: "
            f"{self.login_dt.strftime('%d/%m/%Y %H:%M')}"
        )
        session_label = QtWidgets.QLabel(session_text)
        session_label.setStyleSheet(
            "font-size: 11px; color: #9ca3af;"
        )

        # Botão de alternância de tema no topo. Cria aqui para que
        # apareça na linha superior. A instância é atribuída a
        # ``self.toggle_theme_btn`` para uso em outras funções.
        self.toggle_theme_btn = QtWidgets.QPushButton()
        # Define o texto inicial do botão conforme o tema atual
        if getattr(self, "_current_theme", "dark") == "dark":
            self.toggle_theme_btn.setText("Tema Claro")
        else:
            self.toggle_theme_btn.setText("Tema Escuro")
        self.toggle_theme_btn.clicked.connect(self._toggle_theme)
        self.toggle_theme_btn.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        # Altura compatível com a barra superior
        self.toggle_theme_btn.setFixedHeight(28)

        top_layout.addWidget(title_label)
        top_layout.addWidget(spacer)
        top_layout.addWidget(session_label)
        top_layout.addWidget(self.toggle_theme_btn)

        # Background colour for top bar
        top_bar.setStyleSheet(
            "background-color: #020617; border-bottom: 1px solid #1f2937;"
        )
        return top_bar

    def _populate_pages(self) -> None:
        """
        Populate the sidebar and stack with pages. Each entry in
        ``_menu_items`` consists of a display label and a widget instance.
        When a new page class is added, append an entry here.
        """
        # List of tuples: (display text, widget)
        menu_pages: List[Tuple[str, QtWidgets.QWidget]] = []

        # Dashboard
        menu_pages.append(("Dashboard", self._build_placeholder_page("Dashboard")))

        # Perfil
        menu_pages.append(("Perfil", self._build_placeholder_page("Perfil")))

        # Financeiro (Transações)
        # Use real TransactionsView; pass apenas o código da empresa
        menu_pages.append(("Financeiro", TransactionsView(self.codigoempresa)))

        # Cartões de Crédito
        menu_pages.append(("Cartões", self._build_placeholder_page("Cartões de Crédito")))

        # Folha de Pagamento
        menu_pages.append(("Folha", self._build_placeholder_page("Folha de Pagamento")))

        # Recorrentes
        # Use real RecorrentesView; pass apenas o código da empresa
        menu_pages.append(("Recorrentes", RecorrentesView(self.codigoempresa)))

        # Orçamentos
        orcamentos_view = OrcamentosView(self.codigoempresa)
        menu_pages.append(("Orçamentos", orcamentos_view))

        # Contas (bancárias)
        contas_view = AccountsView(self.codigoempresa)
        menu_pages.append(("Contas", contas_view))

        # Contas a Vencer
        menu_pages.append(("Contas a Vencer", self._build_placeholder_page("Contas a Vencer")))

        # Calendário
        menu_pages.append(("Calendário", self._build_placeholder_page("Calendário")))

        # Relatórios
        menu_pages.append(("Relatórios", self._build_placeholder_page("Relatórios")))

        # Categorias & Tipos
        categories_view = CategoriesView(self.codigoempresa)
        menu_pages.append(("Categorias", categories_view))

        # Chat IA
        menu_pages.append(("Chat IA", self._build_placeholder_page("Chat IA")))

        # Acesso Rápido IA
        menu_pages.append(("Acesso Rápido IA", self._build_placeholder_page("Acesso Rápido IA")))

        # Configurações
        menu_pages.append(("Configurações", self._build_placeholder_page("Configurações")))

        # Logs
        menu_pages.append(("Logs", self._build_placeholder_page("Logs")))

        # Prepara ícones para cada item. O arquivo de ícone deve existir
        # em ``ui/icons``. Se o ícone não for encontrado, a linha será
        # exibida apenas com texto.
        icon_map = {
            "Dashboard": "dashboard.png",
            "Perfil": "perfil.png",
            "Financeiro": "financeiro.png",
            "Cartões": "cartoes.png",
            "Folha": "folha.png",
            "Recorrentes": "recorrentes.png",
            "Orçamentos": "orcamentos.png",
            "Contas": "Contas.png",
            "Contas a Vencer": "contas_a_vencer.png",
            "Calendário": "calendario.png",
            "Relatórios": "relatorios.png",
            "Categorias": "categorias.png",
            "Chat IA": "chat_ia.png",
            "Acesso Rápido IA": "acesso_rapido_ia.png",
            "Configurações": "configuracoes.png",
            "Logs": "logs.png",
        }

        # Fill sidebar and stack
        for label, widget in menu_pages:
            # Obtém o caminho do ícone, se existir
            filename = icon_map.get(label)
            if filename:
                icon_path = f"ui/icons/{filename}"
                icon = QtGui.QIcon(icon_path)
                item = QtWidgets.QListWidgetItem(icon, label)
            else:
                item = QtWidgets.QListWidgetItem(label)
            self.sidebar.addItem(item)
            self.stack.addWidget(widget)

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------
    def _toggle_theme(self) -> None:
        """
        Alterna entre os temas claro e escuro.

        Ao alternar, a folha de estilos (QSS) é reaplicada via
        ``apply_theme`` e o texto do botão é atualizado para indicar
        qual tema será aplicado na próxima alternância.
        """
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        from ui.theme import apply_theme  # import local para evitar ciclos
        # Alterna o tema atual
        if getattr(self, "_current_theme", "dark") == "dark":
            # Mudar para claro
            apply_theme(app, "light")
            self._current_theme = "light"
            self.toggle_theme_btn.setText("Tema Escuro")
        else:
            # Mudar para escuro
            apply_theme(app, "dark")
            self._current_theme = "dark"
            self.toggle_theme_btn.setText("Tema Claro")

        # Após alternar o tema, notifique todas as páginas que suportam atualização de tema
        for idx in range(self.stack.count()):
            widget = self.stack.widget(idx)
            # Se o widget (ou seu atributo central) tiver método set_theme, chame
            if hasattr(widget, "set_theme"):
                try:
                    widget.set_theme(self._current_theme)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_placeholder_page(self, title: str) -> QtWidgets.QWidget:
        """
        Create a simple placeholder page with a title and a message
        indicating that the feature is under construction.

        Parameters
        ----------
        title: str
            The heading to display on the page.

        Returns
        -------
        QtWidgets.QWidget
            The placeholder widget.
        """
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #e5e7eb;"
        )

        subtitle = QtWidgets.QLabel(
            "Página em construção. Esta funcionalidade será implementada em breve."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            "font-size: 13px; color: #9ca3af;"
        )

        layout.addWidget(title_label)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        return page