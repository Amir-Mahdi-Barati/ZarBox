#zarbox

import sys
import pickle
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QComboBox, QListWidget, QFileDialog, QMessageBox,
    QLabel, QHBoxLayout, QScrollArea, QFrame, QCheckBox, QTabWidget,
    QDialog, QTextEdit, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QCursor
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from bidi.algorithm import get_display
import arabic_reshaper
import re
import datetime
import webbrowser
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.font_manager as fm

# Check if Vazir font file exists and register it
FONT_PATH = 'Vazir.ttf'
FONT_NAME = 'Vazir'
FALLBACK_FONT = 'Helvetica'

def register_fonts():
    """Register Vazir font for PDF and UI, with fallback to Helvetica"""
    global FONT_NAME
    try:
        if os.path.exists(FONT_PATH):
            pdfmetrics.registerFont(TTFont('Vazir', FONT_PATH))
            # Register font for matplotlib
            fm.fontManager.addfont(FONT_PATH)
            plt.rcParams['font.family'] = 'Vazir'
        else:
            raise FileNotFoundError("Vazir.ttf not found")
    except Exception as e:
        print(f"Font registration failed: {e}. Falling back to {FALLBACK_FONT}")
        FONT_NAME = FALLBACK_FONT
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = [FALLBACK_FONT]

# Register fonts at startup
register_fonts()

# Load Vazir font for Qt UI
def load_qt_font():
   
    font_db = QFontDatabase()
    if os.path.exists(FONT_PATH):
        font_id = font_db.addApplicationFont(FONT_PATH)
        if font_id != -1:
            font_families = font_db.applicationFontFamilies(font_id)
            if font_families:
                return QFont(font_families[0], 10)
    return QFont(FALLBACK_FONT, 10)

def reshape(text):
    """Reshape Persian text for correct display"""
    return get_display(arabic_reshaper.reshape(str(text)))

class EditOrderDialog(QDialog):
    """Dialog for editing orders"""
    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ویرایش سفارش")
        self.setFixedSize(700, 600)
        self.order = order
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Buyer info
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignRight)
        form_layout.setSpacing(1)
        self.buyer_name = QLineEdit(self.order['buyer_name'])
        self.buyer_phone = QLineEdit(self.order['buyer_phone'])
        self.buyer_address = QLineEdit(self.order['buyer_address'])
        self.buyer_postal = QLineEdit(self.order['buyer_postal'])
        self.buyer_country = QLineEdit(self.order['buyer_country'])
        
        form_layout.addRow("👤 نام مشتری", self.buyer_name)
        form_layout.addRow("📱 شماره تماس مشتری", self.buyer_phone)
        form_layout.addRow("📦 آدرس مشتری", self.buyer_address)
        form_layout.addRow("🏤 کد پستی", self.buyer_postal)
        form_layout.addRow("🌍 کشور", self.buyer_country)
        layout.addLayout(form_layout)

        # Items display
        self.items_text = QTextEdit()
        self.items_text.setReadOnly(True)
        items_str = "\n".join([(f"{item[0]} | {item[1]:,.0f} × {item[2]} {item[3]} = {item[4]:,.0f} تومان")
                              for item in self.order['items']])
        self.items_text.setText(items_str)
        self.items_text.setFixedHeight(200)
        layout.addWidget(self.items_text)

        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 ذخیره")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("❌ لغو")
        cancel_btn.clicked.connect(self.reject)
        for btn in [save_btn, cancel_btn]:
            btn.setFixedWidth(150)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def get_updated_order(self):
        """Return updated order information"""
        return {
            'date': self.order['date'],
            'seller_name': self.order['seller_name'],
            'seller_phone': self.order['seller_phone'],
            'seller_email': self.order['seller_email'],
            'seller_address': self.order['seller_address'],
            'buyer_name': self.buyer_name.text().strip(),
            'buyer_phone': self.buyer_phone.text().strip(),
            'buyer_address': self.buyer_address.text().strip(),
            'buyer_postal': self.buyer_postal.text().strip(),
            'buyer_country': self.buyer_country.text().strip(),
            'items': self.order['items'],
            'total': self.order['total']
        }

class InvoiceApp(QWidget):
    def __init__(self):
        super().__init__()
        self.items = []
        self.registered_orders = []
        self.unregistered_orders = []
        self.data_file = "orders.pkl"
        self.is_dark_theme = False
        self.load_data()
        self.init_ui()
        self.setWindowTitle("پیش فاکتور")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setFixedSize(1280, 720)

    def load_data(self):
        """Load order data from file silently"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'rb') as f:
                    data = pickle.load(f)
                    self.registered_orders = data.get('registered', [])
                    self.unregistered_orders = data.get('unregistered', [])
            else:
                self.registered_orders = []
                self.unregistered_orders = []
        except (pickle.UnpicklingError, EOFError, AttributeError):
            self.registered_orders = []
            self.unregistered_orders = []

    def save_data(self):
        """Save orders to file silently"""
        try:
            with open(self.data_file, 'wb') as f:
                pickle.dump({
                    'registered': self.registered_orders,
                    'unregistered': self.unregistered_orders
                }, f)
        except Exception:
            pass

    def init_ui(self):
        """Initialize main UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(12)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(10)
        minimize_btn = QPushButton("◀▶")
        minimize_btn.setFixedSize(45,45)
        minimize_btn.setObjectName("minimizeBtn")
        minimize_btn.clicked.connect(self.showMinimized)
        close_btn = QPushButton("×")
        close_btn.setFixedSize(45, 45)
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.close)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(minimize_btn)
        toolbar_layout.addWidget(close_btn)
        main_layout.addLayout(toolbar_layout)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setFont(load_qt_font())
        self.tabs.setFixedHeight(600)
        main_layout.addWidget(self.tabs)

        # Home Tab
        self.home_tab = QWidget()
        self.home_layout = QVBoxLayout(self.home_tab)
        self.setup_home_ui()
        self.tabs.addTab(self.home_tab, "🏠 خانه")

        # Orders Tab
        self.orders_tab = QWidget()
        self.orders_layout = QVBoxLayout(self.orders_tab)
        self.setup_orders_ui()
        self.tabs.addTab(self.orders_tab, "📋 سفارشات")

        # Statistics Tab
        self.stats_tab = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_tab)
        self.setup_statistics_ui()
        self.tabs.addTab(self.stats_tab, "📊 آمار و اطلاعات")

        # Footer
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)
        self.theme_toggle = QCheckBox("حالت تیره/روشن")
        self.theme_toggle.setChecked(False)
        self.theme_toggle.setFont(load_qt_font())
        self.theme_toggle.stateChanged.connect(self.toggle_theme)
        footer_layout.addWidget(self.theme_toggle)

        github_label = QLabel("GitHub")
        github_label.setFont(load_qt_font())
        github_label.setObjectName("githubLabel")
        github_label.setCursor(QCursor(Qt.PointingHandCursor))
        github_label.mousePressEvent = lambda event: webbrowser.open("https://github.com/Amir-Mahdi-Barati")
        footer_layout.addWidget(github_label)
        footer_layout.addStretch()
        main_layout.addLayout(footer_layout)

        self.apply_theme()

    def setup_home_ui(self):
        """Setup UI for Home tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 0px; } QScrollBar:horizontal { height: 0px; }")
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setAlignment(Qt.AlignTop)
        self.home_layout.addWidget(scroll)

        # Header
        header_label = QLabel("🧾مدیریت فروش")
        header_label.setFont(QFont(FONT_NAME, 14, QFont.Bold))
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setObjectName("headerLabel")
        content_layout.addWidget(header_label)

        # Seller and Buyer info
        info_container = QHBoxLayout()
        info_container.setSpacing(12)

        seller_frame = QFrame()
        seller_frame.setObjectName("infoFrame")
        seller_frame.setFixedWidth(580)
        seller_layout = QFormLayout()
        seller_layout.setLabelAlignment(Qt.AlignRight)
        seller_layout.setFormAlignment(Qt.AlignRight)
        seller_layout.setSpacing(10)
        self.seller_name = QLineEdit()
        self.seller_phone = QLineEdit()
        self.seller_phone.setPlaceholderText("مثال: 09123456789")
        self.seller_email = QLineEdit()
        self.seller_email.setPlaceholderText("مثال: example@email.com")
        self.seller_address = QLineEdit()
        
        seller_layout.addRow("🏢 نام فرشگاه", self.seller_name)
        seller_layout.addRow("📞 تلفن فروشنده", self.seller_phone)
        seller_layout.addRow("📧 ایمیل فروشنده", self.seller_email)
        seller_layout.addRow("📍 آدرس فروشنده", self.seller_address)
        seller_frame.setLayout(seller_layout)
        info_container.addWidget(seller_frame)

        buyer_frame = QFrame()
        buyer_frame.setObjectName("infoFrame")
        buyer_frame.setFixedWidth(580)
        buyer_layout = QFormLayout()
        buyer_layout.setLabelAlignment(Qt.AlignRight)
        buyer_layout.setFormAlignment(Qt.AlignRight)
        buyer_layout.setSpacing(10)
        self.buyer_name = QLineEdit()
        self.buyer_phone = QLineEdit()
        self.buyer_phone.setPlaceholderText("مثال: 09123456789")
        self.buyer_address = QLineEdit()
        self.buyer_postal = QLineEdit()
        self.buyer_country = QLineEdit()
        
        buyer_layout.addRow("👤 نام مشتری", self.buyer_name)
        buyer_layout.addRow("📱 شماره تماس مشتری", self.buyer_phone)
        buyer_layout.addRow("📦 آدرس مشتری", self.buyer_address)
        buyer_layout.addRow("🏤 کد پستی", self.buyer_postal)
        buyer_layout.addRow("🌍 کشور", self.buyer_country)
        buyer_frame.setLayout(buyer_layout)
        info_container.addWidget(buyer_frame)
        
        content_layout.addLayout(info_container)

        # Item input
        item_frame = QFrame()
        item_frame.setObjectName("infoFrame")
        item_frame.setFixedWidth(1180)
        item_layout = QFormLayout()
        item_layout.setLabelAlignment(Qt.AlignRight)
        item_layout.setFormAlignment(Qt.AlignRight)
        item_layout.setSpacing(10)
        self.item_name = QLineEdit()
        self.item_price = QLineEdit()
        self.item_price.setPlaceholderText("مثال: 100000")
        self.item_quantity = QLineEdit()
        self.item_quantity.setPlaceholderText("مثال: 5")
        self.item_unit = QComboBox()
        self.item_unit.addItems(["عدد", "کیلوگرم", "متر", "بسته", "کارتن"])
        
        item_layout.addRow("📦 نام کالا:", self.item_name)
        item_layout.addRow("💵 قیمت واحد:", self.item_price)
        item_layout.addRow("🔢 تعداد:", self.item_quantity)
        item_layout.addRow("📏 واحد:", self.item_unit)
        item_frame.setLayout(item_layout)
        content_layout.addWidget(item_frame)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        self.btn_add = QPushButton("➕ افزودن کالا")
        self.btn_add.clicked.connect(self.add_item)
        self.btn_clear = QPushButton("🗑️ پاک کردن لیست")
        self.btn_clear.clicked.connect(self.clear_items)
        self.btn_delete = QPushButton("❌ حذف کالا")
        self.btn_delete.setObjectName("deleteBtn")
        self.btn_delete.clicked.connect(self.delete_item)
        self.btn_add_to_registered = QPushButton("✅ ثبت سفارش")
        self.btn_add_to_registered.clicked.connect(self.add_to_registered_orders)
        self.btn_add_to_unregistered = QPushButton("📥ثبت موقت")
        self.btn_add_to_unregistered.clicked.connect(self.add_to_unregistered_orders)
        self.btn_export = QPushButton("📄 صدور PDF")
        self.btn_export.clicked.connect(self.export_pdf)
        
        for btn in [self.btn_add, self.btn_clear, self.btn_delete, 
                    self.btn_add_to_registered, self.btn_add_to_unregistered, self.btn_export]:
            btn.setFixedWidth(190)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_clear)
        button_layout.addWidget(self.btn_delete)
        button_layout.addWidget(self.btn_add_to_registered)
        button_layout.addWidget(self.btn_add_to_unregistered)
        button_layout.addWidget(self.btn_export)
        content_layout.addLayout(button_layout)

        # Item list
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("itemList")
        self.list_widget.setSpacing(8)
        self.list_widget.setFixedSize(1180, 180)
        content_layout.addWidget(self.list_widget)

        # Total label
        self.total_label = QLabel("جمع کل: ۰ تومان")
        self.total_label.setFont(QFont(FONT_NAME, 11, QFont.Bold))
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setFixedWidth(1180)
        content_layout.addWidget(self.total_label)

    def setup_orders_ui(self):
        """Setup UI for Orders tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 0px; } QScrollBar:horizontal { height: 0px; }")
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setAlignment(Qt.AlignTop)
        self.orders_layout.addWidget(scroll)

        # Registered orders
        reg_label = QLabel("📋 سفارشات ثبت شده")
        reg_label.setFont(QFont(FONT_NAME, 13, QFont.Bold))
        reg_label.setAlignment(Qt.AlignCenter)
        reg_label.setObjectName("headerLabel")
        content_layout.addWidget(reg_label)

        self.orders_list = QListWidget()
        self.orders_list.setObjectName("itemList")
        self.orders_list.setSpacing(8)
        self.orders_list.setFixedSize(1180, 200)
        self.orders_list.itemDoubleClicked.connect(lambda item: self.edit_order(item, True))
        content_layout.addWidget(self.orders_list)

        reg_button_layout = QHBoxLayout()
        self.btn_delete_order = QPushButton("❌حذف سفارشات")
        self.btn_delete_order.setObjectName("deleteBtn")
        self.btn_delete_order.setFixedWidth(200)
        self.btn_delete_order.clicked.connect(self.delete_registered_order)
        reg_button_layout.addWidget(self.btn_delete_order)
        reg_button_layout.addStretch()
        content_layout.addLayout(reg_button_layout)

        # Unregistered orders
        unreg_label = QLabel("📋 سفارشات ثبت نشده")
        unreg_label.setFont(QFont(FONT_NAME, 13, QFont.Bold))
        unreg_label.setAlignment(Qt.AlignCenter)
        unreg_label.setObjectName("headerLabel")
        content_layout.addWidget(unreg_label)

        self.unreg_orders_list = QListWidget()
        self.unreg_orders_list.setObjectName("itemList")
        self.unreg_orders_list.setSpacing(8)
        self.unreg_orders_list.setFixedSize(1180, 200)
        self.unreg_orders_list.itemDoubleClicked.connect(lambda item: self.edit_order(item, False))
        content_layout.addWidget(self.unreg_orders_list)

        unreg_button_layout = QHBoxLayout()
        self.btn_delete_unreg_order = QPushButton("❌حذف سفارشات")
        self.btn_delete_unreg_order.setObjectName("deleteBtn")
        self.btn_delete_unreg_order.setFixedWidth(200)
        self.btn_delete_unreg_order.clicked.connect(self.delete_unregistered_order)
        self.btn_move_to_registered = QPushButton("انتقال به ثبت شده")
        self.btn_move_to_registered.setObjectName("moveBtn")
        self.btn_move_to_registered.setFixedWidth(200)
        self.btn_move_to_registered.clicked.connect(self.move_to_registered)
        unreg_button_layout.addWidget(self.btn_delete_unreg_order)
        unreg_button_layout.addWidget(self.btn_move_to_registered)
        unreg_button_layout.addStretch()
        content_layout.addLayout(unreg_button_layout)

        self.update_registered_orders_list()
        self.update_unregistered_orders_list()

    def setup_statistics_ui(self):
        """Setup UI for Statistics tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 0px; } QScrollBar:horizontal { height: 0px; }")
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setAlignment(Qt.AlignTop)
        self.stats_layout.addWidget(scroll)

        stats_label = QLabel("📊 آمار و اطلاعات")
        stats_label.setFont(QFont(FONT_NAME, 13, QFont.Bold))
        stats_label.setAlignment(Qt.AlignCenter)
        stats_label.setObjectName("headerLabel")
        content_layout.addWidget(stats_label)

        # Statistics table
        self.stats_table = QTableWidget()
        self.stats_table.setObjectName("statsTable")
        self.stats_table.setFixedSize(1180, 120)
        self.stats_table.setRowCount(4)
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels([("مقدار"), ("مورد")])
        self.stats_table.setFont(load_qt_font())
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setColumnWidth(0, 200)
        self.stats_table.setStyleSheet(f"""
            QTableWidget#statsTable {{
                font-family: {FONT_NAME};
                font-size: 10pt;
                border: 1px solid #555555;
                border-radius: 4px;
            }}
            QTableWidget#statsTable::item {{
                padding: 10px;
                text-align: center;
            }}
            QHeaderView::section {{
                font-family: {FONT_NAME};
                font-size: 10pt;
                padding: 8px;
                background-color: #1976D2;
                color: white;
                border: none;
            }}
        """)
        content_layout.addWidget(self.stats_table)

        # Pie charts container
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(12)

        # Registered orders pie chart
        self.figure_reg = plt.Figure(figsize=(5, 2.5))
        self.canvas_reg = FigureCanvas(self.figure_reg)
        self.canvas_reg.setFixedSize(580, 250)
        charts_layout.addWidget(self.canvas_reg)

        # Unregistered orders pie chart
        self.figure_unreg = plt.Figure(figsize=(5, 2.5))
        self.canvas_unreg = FigureCanvas(self.figure_unreg)
        self.canvas_unreg.setFixedSize(580, 250)
        charts_layout.addWidget(self.canvas_unreg)

        content_layout.addLayout(charts_layout)

        self.btn_clear_data = QPushButton("🗑️حذف تمامی داده‌ها")
        self.btn_clear_data.setObjectName("deleteBtn")
        self.btn_clear_data.setFixedWidth(200)
        self.btn_clear_data.clicked.connect(self.clear_all_data)
        content_layout.addWidget(self.btn_clear_data)

        self.update_statistics()

    def update_statistics(self):
        """Update statistics table and pie charts"""
        total_reg_orders = len(self.registered_orders)
        total_unreg_orders = len(self.unregistered_orders)
        total_amount = sum(sum(item[4] for item in order['items']) for order in self.registered_orders)
        avg_order = total_amount / total_reg_orders if total_reg_orders > 0 else 0

        # Update table
        table_data = [
            ((f"{total_reg_orders}"),("تعداد سفارشات ثبت شده")),
            ((f"{total_unreg_orders}"),("تعداد سفارشات ثبت نشده")),
            ((f"{total_amount:,.0f} تومان"),("جمع کل فروش (سفارشات ثبت شده)")),
            ((f"{avg_order:,.0f} تومان"),("میانگین هر سفارش (ثبت شده)"))
        ]
        for row, (value, desc) in enumerate(table_data):
            value_item = QTableWidgetItem(value)
            desc_item = QTableWidgetItem(desc)
            value_item.setTextAlignment(Qt.AlignCenter)
            desc_item.setTextAlignment(Qt.AlignCenter)
            value_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            desc_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            value_item.setFont(load_qt_font())
            desc_item.setFont(load_qt_font())
            self.stats_table.setItem(row, 0, value_item)
            self.stats_table.setItem(row, 1, desc_item)

        # Registered orders pie chart
        self.figure_reg.clear()
        ax_reg = self.figure_reg.add_subplot(111)
        labels_reg = [reshape('سفارشات ثبت شده'), reshape('بدون سفارش')]
        sizes_reg = [total_reg_orders, 1 if total_reg_orders == 0 else 0]
        colors_reg = ['#1976D2', '#B0BEC5']
        ax_reg.pie(sizes_reg, labels=labels_reg, colors=colors_reg, autopct='%1.1f%%', startangle=90, textprops={'fontfamily': FONT_NAME, 'fontsize': 10})
        ax_reg.set_title(reshape("وضعیت سفارشات ثبت شده"), fontfamily=FONT_NAME, fontsize=12)
        self.canvas_reg.draw()

        # Unregistered orders pie chart
        self.figure_unreg.clear()
        ax_unreg = self.figure_unreg.add_subplot(111)
        labels_unreg = [reshape('سفارشات ثبت نشده'), reshape('بدون سفارش')]
        sizes_unreg = [total_unreg_orders, 1 if total_unreg_orders == 0 else 0]
        colors_unreg = ['#D32F2F', '#B0BEC5']
        ax_unreg.pie(sizes_unreg, labels=labels_unreg, colors=colors_unreg, autopct='%1.1f%%', startangle=90, textprops={'fontfamily': FONT_NAME, 'fontsize': 10})
        ax_unreg.set_title(reshape("وضعیت سفارشات ثبت نشده"), fontfamily=FONT_NAME, fontsize=12)
        self.canvas_unreg.draw()

    def update_registered_orders_list(self):
        """Update list of registered orders"""
        self.orders_list.clear()
        for i, order in enumerate(self.registered_orders):
            total = sum(item[4] for item in order['items'])
            self.orders_list.addItem(
                (f"سفارش #{i+1} | مشتری: {order['buyer_name']} | تاریخ: {order['date']} | جمع: {total:,.0f} تومان")
            )

    def update_unregistered_orders_list(self):
        """Update list of unregistered orders"""
        self.unreg_orders_list.clear()
        for i, order in enumerate(self.unregistered_orders):
            total = sum(item[4] for item in order['items'])
            self.unreg_orders_list.addItem(
                (f"سفارش #{i+1} | مشتری: {order['buyer_name']} | تاریخ: {order['date']} | جمع: {total:,.0f} تومان")
            )

    def edit_order(self, item, is_registered):
        """Edit selected order"""
        row = self.orders_list.row(item) if is_registered else self.unreg_orders_list.row(item)
        order_list = self.registered_orders if is_registered else self.unregistered_orders
        order = order_list[row]
        
        dialog = EditOrderDialog(order, self)
        if dialog.exec_():
            updated_order = dialog.get_updated_order()
            if not updated_order['buyer_name'].strip():
                QMessageBox.warning(self, "خطا", "نام مشتری نمی‌تواند خالی باشد.")
                return
            if updated_order['buyer_phone'] and not re.match(r'^09\d{9}$', updated_order['buyer_phone']):
                QMessageBox.warning(self, "خطا", "شماره تلفن مشتری باید معتبر باشد (مثال: 09123456789).")
                return
            order_list[row] = updated_order
            self.save_data()
            if is_registered:
                self.update_registered_orders_list()
            else:
                self.update_unregistered_orders_list()
            self.update_statistics()
            QMessageBox.information(self, "موفقیت", "سفارش با موفقیت ویرایش شد.")

    def move_to_registered(self):
        """Move unregistered order to registered"""
        selected_items = self.unreg_orders_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "خطا", "لطفاً یک سفارش ثبت نشده انتخاب کنید.")
            return
        if QMessageBox.question(self, "تأیید", "آیا مطمئن هستید که می‌خواهید این سفارش را به ثبت شده منتقل کنید؟",
                              QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            row = self.unreg_orders_list.row(selected_items[0])
            order = self.unregistered_orders.pop(row)
            self.registered_orders.append(order)
            self.save_data()
            self.update_registered_orders_list()
            self.update_unregistered_orders_list()
            self.update_statistics()
            QMessageBox.information(self, "موفقیت", "سفارش با موفقیت به ثبت شده منتقل شد.")

    def apply_theme(self):
        """Apply dark or light theme"""
        if self.is_dark_theme:
            stylesheet = """
                QWidget {
                    background-color: #212121;
                    color: #E0E0E0;
                    font-family: """ + FONT_NAME + """;
                    font-size: 11pt;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background: #2D2D2D;
                }
                QTabBar::tab {
                    background: #2D2D2D;
                    color: #E0E0E0;
                    padding: 8px 16px;
                    margin: 4px;
                    border-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #1976D2;
                    color: white;
                }
                QLabel {
                    background: transparent;
                    color: #E0E0E0;
                    padding: 8px;
                    margin: 2px;
                }
                QLineEdit, QComboBox, QTextEdit {
                    background-color: #2D2D2D;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    color: #E0E0E0;
                    text-align: right;
                    margin-bottom: 8px;
                }
                QComboBox {
                    padding-right: 12px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 16px;
                }
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: 1px solid #1565C0;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 11pt;
                    margin-top: 8px;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
                QPushButton#minimizeBtn {
                    background-color: #424242;
                    border: 1px solid #616161;
                    border-radius: 4px;
                }
                QPushButton#minimizeBtn:hover {
                    background-color: #616161;
                }
                QPushButton#minimizeBtn:pressed {
                    background-color: #212121;
                }
                QPushButton#closeBtn, QPushButton#deleteBtn {
                    background-color: #D32F2F;
                    border: 1px solid #B71C1C;
                    border-radius: 4px;
                }
                QPushButton#closeBtn:hover, QPushButton#deleteBtn:hover {
                    background-color: #B71C1C;
                }
                QPushButton#closeBtn:pressed, QPushButton#deleteBtn:pressed {
                    background-color: #7F0000;
                }
                QPushButton#moveBtn {
                    background-color: #388E3C;
                    border: 1px solid #2E7D32;
                    border-radius: 4px;
                }
                QPushButton#moveBtn:hover {
                    background-color: #2E7D32;
                }
                QPushButton#moveBtn:pressed {
                    background-color: #1B5E20;
                }
                QFrame#infoFrame {
                    background-color: #2D2D2D;
                    border: 1px solid #555555;
                    border-radius: 6px;
                    padding: 12px;
                }
                QListWidget#itemList {
                    background-color: #2D2D2D;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    color: #E0E0E0;
                }
                QTableWidget#statsTable {
                    background-color: #2D2D2D;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    color: #E0E0E0;
                    gridline-color: #555555;
                    font-family: """ + FONT_NAME + """;
                    font-size: 10pt;
                }
                QTableWidget#statsTable::item {
                    padding: 10px;
                    text-align: center;
                }
                QHeaderView::section {
                    font-family: """ + FONT_NAME + """;
                    font-size: 10pt;
                    padding: 8px;
                    background-color: #1976D2;
                    color: white;
                    border: none;
                }
                QCheckBox {
                    color: #E0E0E0;
                    padding: 8px;
                    font-size: 10pt;
                    font-weight: bold;
                }
                QLabel#headerLabel {
                    background: transparent;
                    color: #64B5F6;
                    border-bottom: 2px solid #1976D2;
                    padding: 8px;
                    margin: 2px;
                    font-size: 13pt;
                }
                QLabel#githubLabel {
                    color: #64B5F6;
                    padding: 8px;
                    font-size: 10pt;
                    font-weight: bold;
                }
                QLabel#githubLabel:hover {
                    color: #BBDEFB;
                }
            """
        else:
            stylesheet = """
                QWidget {
                    background-color: #F5F6FA;
                    color: #1A2526;
                    font-family: """ + FONT_NAME + """;
                    font-size: 11pt;
                }
                QTabWidget::pane {
                    border: 1px solid #B0BEC5;
                    background: #FFFFFF;
                }
                QTabBar::tab {
                    background: #E0E0E0;
                    color: #1A2526;
                    padding: 8px 16px;
                    margin: 4px;
                    border-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #1976D2;
                    color: white;
                }
                QLabel {
                    background: transparent;
                    color: #1A2526;
                    padding: 8px;
                    margin: 2px;
                }
                QLineEdit, QComboBox, QTextEdit {
                    background-color: #FFFFFF;
                    border: 1px solid #B0BEC5;
                    border-radius: 4px;
                    padding: 8px;
                    color: #1A2526;
                    text-align: right;
                    margin-bottom: 8px;
                }
                QComboBox {
                    padding-right: 12px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 16px;
                }
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: 1px solid #1565C0;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 11pt;
                    margin-top: 8px;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
                QPushButton#minimizeBtn {
                    background-color: #E0E0E0;
                    border: 1px solid #B0BEC5;
                    border-radius: 4px;
                }
                QPushButton#minimizeBtn:hover {
                    background-color: #B0BEC5;
                }
                QPushButton#minimizeBtn:pressed {
                    background-color: #90A4AE;
                }
                QPushButton#closeBtn, QPushButton#deleteBtn {
                    background-color: #D32F2F;
                    border: 1px solid #B71C1C;
                    border-radius: 4px;
                }
                QPushButton#closeBtn:hover, QPushButton#deleteBtn:hover {
                    background-color: #B71C1C;
                }
                QPushButton#closeBtn:pressed, QPushButton#deleteBtn:pressed {
                    background-color: #7F0000;
                }
                QPushButton#moveBtn {
                    background-color: #388E3C;
                    border: 1px solid #2E7D32;
                    border-radius: 4px;
                }
                QPushButton#moveBtn:hover {
                    background-color: #2E7D32;
                }
                QPushButton#moveBtn:pressed {
                    background-color: #1B5E20;
                }
                QFrame#infoFrame {
                    background-color: #FFFFFF;
                    border: 1px solid #B0BEC5;
                    border-radius: 6px;
                    padding: 12px;
                }
                QListWidget#itemList {
                    background-color: #FFFFFF;
                    border: 1px solid #B0BEC5;
                    border-radius: 4px;
                    padding: 8px;
                    color: #1A2526;
                }
                QTableWidget#statsTable {
                    background-color: #FFFFFF;
                    border: 1px solid #B0BEC5;
                    border-radius: 4px;
                    color: #1A2526;
                    gridline-color: #B0BEC5;
                    font-family: """ + FONT_NAME + """;
                    font-size: 10pt;
                }
                QTableWidget#statsTable::item {
                    padding: 10px;
                    text-align: center;
                }
                QHeaderView::section {
                    font-family: """ + FONT_NAME + """;
                    font-size: 10pt;
                    padding: 8px;
                    background-color: #1976D2;
                    color: white;
                    border: none;
                }
                QCheckBox {
                    color: #1A2526;
                    padding: 8px;
                    font-size: 10pt;
                    font-weight: bold;
                }
                QLabel#headerLabel {
                    background: transparent;
                    color: #1976D2;
                    border-bottom: 2px solid #1976D2;
                    padding: 8px;
                    margin: 2px;
                    font-size: 13pt;
                }
                QLabel#githubLabel {
                    color: #1976D2;
                    padding: 8px;
                    font-size: 10pt;
                    font-weight: bold;
                }
                QLabel#githubLabel:hover {
                    color: #1565C0;
                }
            """
        self.setStyleSheet(stylesheet)

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()

    def validate_inputs(self):
        """Validate input fields"""
        if not self.seller_name.text().strip():
            return False, "نام فروشنده نمی‌تواند خالی باشد."
        if not self.buyer_name.text().strip():
            return False, "نام مشتری نمی‌تواند خالی باشد."
        if self.seller_phone.text() and not re.match(r'^09\d{9}$', self.seller_phone.text()):
            return False, "شماره تلفن فروشنده باید معتبر باشد (مثال: 09123456789)."
        if self.buyer_phone.text() and not re.match(r'^09\d{9}$', self.buyer_phone.text()):
            return False, "شماره تلفن مشتری باید معتبر باشد (مثال: 09123456789)."
        if self.seller_email.text() and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', self.seller_email.text()):
            return False, "ایمیل فروشنده باید معتبر باشد."
        return True, ""

    def add_item(self):
        """Add item to invoice"""
        name = self.item_name.text().strip()
        if not name:
            QMessageBox.warning(self, "خطا", "نام کالا نمی‌تواند خالی باشد.")
            return
        
        try:
            price = float(self.item_price.text().replace(",", "").strip())
            quantity = float(self.item_quantity.text().strip())
            if price <= 0 or quantity <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "خطا", "قیمت و تعداد باید اعداد مثبت باشند.")
            return

        unit = self.item_unit.currentText()
        total = price * quantity
        self.items.append((name, price, quantity, unit, total))
        self.list_widget.addItem((f"{name} | {price:,.0f} × {quantity} {unit} = {total:,.0f} تومان"))
        self.update_total()

        self.item_name.clear()
        self.item_price.clear()
        self.item_quantity.clear()

    def delete_item(self):
        """Delete selected item from invoice"""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "خطا", "لطفاً یک کالا از لیست انتخاب کنید.")
            return
        if QMessageBox.question(self, "تأیید", "آیا مطمئن هستید که می‌خواهید این کالا را حذف کنید؟",
                              QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            row = self.list_widget.row(selected_items[0])
            self.list_widget.takeItem(row)
            self.items.pop(row)
            self.update_total()

    def delete_registered_order(self):
        """Delete selected registered order"""
        selected_items = self.orders_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "خطا", "لطفاً یک سفارش انتخاب کنید.")
            return
        if QMessageBox.question(self, "تأیید", "آیا مطمئن هستید که می‌خواهید این سفارش را حذف کنید؟",
                              QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            row = self.orders_list.row(selected_items[0])
            self.orders_list.takeItem(row)
            self.registered_orders.pop(row)
            self.save_data()
            self.update_statistics()

    def delete_unregistered_order(self):
        """Delete selected unregistered order"""
        selected_items = self.unreg_orders_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "خطا", "لطفاً یک سفارش انتخاب کنید.")
            return
        if QMessageBox.question(self, "تأیید", "آیا مطمئن هستید که می‌خواهید این سفارش را حذف کنید؟",
                              QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            row = self.unreg_orders_list.row(selected_items[0])
            self.unreg_orders_list.takeItem(row)
            self.unregistered_orders.pop(row)
            self.save_data()
            self.update_statistics()

    def add_to_registered_orders(self):
        """Add invoice to registered orders"""
        valid, error = self.validate_inputs()
        if not valid:
            QMessageBox.warning(self, "خطا", error)
            return

        if not self.items:
            QMessageBox.warning(self, "توجه", "هیچ کالایی ثبت نشده است.")
            return

        total_all = sum(item[4] for item in self.items)
        order = {
            'date': datetime.datetime.now().strftime('%Y/%m/%d'),
            'seller_name': self.seller_name.text(),
            'seller_phone': self.seller_phone.text(),
            'seller_email': self.seller_email.text(),
            'seller_address': self.seller_address.text(),
            'buyer_name': self.buyer_name.text(),
            'buyer_phone': self.buyer_phone.text(),
            'buyer_address': self.buyer_address.text(),
            'buyer_postal': self.buyer_postal.text(),
            'buyer_country': self.buyer_country.text(),
            'items': self.items.copy(),
            'total': total_all
        }
        self.registered_orders.append(order)
        self.save_data()
        self.update_registered_orders_list()
        self.update_statistics()
        self.clear_form()
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(self, "موفقیت", "سفارش با موفقیت ثبت شد.")

    def add_to_unregistered_orders(self):
        """Add invoice to unregistered orders"""
        valid, error = self.validate_inputs()
        if not valid:
            QMessageBox.warning(self, "خطا", error)
            return

        if not self.items:
            QMessageBox.warning(self, "توجه", "هیچ کالایی ثبت نشده است.")
            return

        total_all = sum(item[4] for item in self.items)
        order = {
            'date': datetime.datetime.now().strftime('%Y/%m/%d'),
            'seller_name': self.seller_name.text(),
            'seller_phone': self.seller_phone.text(),
            'seller_email': self.seller_email.text(),
            'seller_address': self.seller_address.text(),
            'buyer_name': self.buyer_name.text(),
            'buyer_phone': self.buyer_phone.text(),
            'buyer_address': self.buyer_address.text(),
            'buyer_postal': self.buyer_postal.text(),
            'buyer_country': self.buyer_country.text(),
            'items': self.items.copy(),
            'total': total_all
        }
        self.unregistered_orders.append(order)
        self.save_data()
        self.update_unregistered_orders_list()
        self.update_statistics()
        self.clear_form()
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(self, "موفقیت", "سفارش با موفقیت به صورت موقت ثبت شد.")

    def clear_form(self):
        """Clear all input fields and item list"""
        self.items.clear()
        self.list_widget.clear()
        self.seller_name.clear()
        self.seller_phone.clear()
        self.seller_email.clear()
        self.seller_address.clear()
        self.buyer_name.clear()
        self.buyer_phone.clear()
        self.buyer_address.clear()
        self.buyer_postal.clear()
        self.buyer_country.clear()
        self.item_name.clear()
        self.item_price.clear()
        self.item_quantity.clear()
        self.update_total()

    def update_total(self):
        """Update total display"""
        total_all = sum(item[4] for item in self.items)
        self.total_label.setText((f"جمع کل: {total_all:,.0f} تومان"))

    def clear_items(self):
        """Clear item list"""
        if QMessageBox.question(self, "تأیید", "آیا مطمئن هستید که می‌خواهید لیست کالاها را پاک کنید؟",
                              QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.items.clear()
            self.list_widget.clear()
            self.update_total()

    def clear_all_data(self):
        """Clear all orders and update UI"""
        if QMessageBox.question(self, "تأیید", "آیا مطمئن هستید که می‌خواهید تمام داده‌ها را حذف کنید؟",
                              QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.registered_orders.clear()
            self.unregistered_orders.clear()
            self.orders_list.clear()
            self.unreg_orders_list.clear()
            self.items.clear()
            self.list_widget.clear()
            self.update_total()
            self.update_statistics()
            self.save_data()
            QMessageBox.information(self, "موفقیت", "تمامی داده‌ها با موفقیت حذف شدند.")

    def export_pdf(self):
        """Export invoice as PDF"""
        valid, error = self.validate_inputs()
        if not valid:
            QMessageBox.warning(self, "خطا", error)
            return

        if not self.items:
            QMessageBox.warning(self, "توجه", "هیچ کالایی ثبت نشده است.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "ذخیره PDF", "", "PDF Files (*.pdf)")
        if not path:
            return

        try:
            c = canvas.Canvas(path, pagesize=A4)
            width, height = A4
            c.setFont(FONT_NAME, 12)

            # Header
            c.setFillColor(HexColor("#1976D2"))
            c.rect(0, height - 40, width, 40, fill=1)
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont(FONT_NAME, 16)
            c.drawCentredString(width/2, height - 28, reshape("پیش‌فاکتور حرفه‌ای"))
            c.setFillColor(HexColor("#000000"))

            y = height - 80

            # Seller and Buyer info
            c.setFont(FONT_NAME, 11)
            c.setFillColor(HexColor("#1A2526"))
            c.drawString(40, y, reshape("اطلاعات فروشنده"))
            c.drawRightString(width - 40, y, reshape("اطلاعات خریدار"))
            y -= 25
            
            c.setFont(FONT_NAME, 10)
            c.drawString(40, y, reshape(f"نام: {self.seller_name.text()}"))
            c.drawRightString(width - 40, y, reshape(f"نام: {self.buyer_name.text()}"))
            y -= 20
            c.drawString(40, y, reshape(f"تلفن: {self.seller_phone.text() or '-'}"))
            c.drawRightString(width - 40, y, reshape(f"تلفن: {self.buyer_phone.text() or '-'}"))
            y -= 20
            
            seller_address = self.wrap_text(self.seller_address.text() or "-", 50)
            buyer_address = self.wrap_text(self.buyer_address.text() or "-", 50)
            max_lines = max(len(seller_address), len(buyer_address))
            
            for i in range(max_lines):
                s_line = seller_address[i] if i < len(seller_address) else ""
                b_line = buyer_address[i] if i < len(buyer_address) else ""
                c.drawString(40, y, reshape(f"آدرس: {s_line}"))
                c.drawRightString(width - 40, y, reshape(f"آدرس: {b_line}"))
                y -= 20
            c.drawRightString(width - 40, y, reshape(f"کد پستی: {self.buyer_postal.text() or '-'}"))
            y -= 20
            c.drawRightString(width - 40, y, reshape(f"کشور: {self.buyer_country.text() or '-'}"))
            y -= 30

            # Items table
            headers = ["ردیف", "نام کالا", "قیمت واحد", "تعداد", "واحد", "قیمت کل"]
            col_widths = [30, 200, 80, 50, 50, 100]
            table_top = y
            row_height = 25

            # Table header
            c.setFillColor(HexColor("#1976D2"))
            c.rect(width - sum(col_widths) - 30, table_top - row_height, sum(col_widths), row_height, fill=1)
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont(FONT_NAME, 11)
            x = width - 30
            for i, header in enumerate(headers):
                c.drawCentredString(x - sum(col_widths[:i]) - col_widths[i]/2, table_top - row_height + 6, reshape(header))
            c.setFillColor(HexColor("#000000"))

            # Table data
            total_all = 0
            y = table_top - row_height
            for idx, (name, price, qty, unit, total) in enumerate(self.items, 1):
                row = [str(idx), name, f"{price:,.0f}", str(qty), unit, f"{total:,.0f}"]
                c.setFillColor(HexColor("#F5F7FA") if idx % 2 else HexColor("#FFFFFF"))
                c.rect(width - sum(col_widths) - 30, y - row_height, sum(col_widths), row_height, fill=1)
                c.setFillColor(HexColor("#000000"))
                for i, cell in enumerate(row):
                    c.drawCentredString(x - sum(col_widths[:i]) - col_widths[i]/2, y - row_height + 6, reshape(cell))
                y -= row_height
                total_all += total

            # Total
            y -= 20
            c.setFont(FONT_NAME, 12)
            c.setFillColor(HexColor("#1976D2"))
            c.drawRightString(width - 30, y, reshape(f"جمع کل: {total_all:,.0f} تومان"))
            c.setFillColor(HexColor("#000000"))

            # Footer
            c.setFont(FONT_NAME, 9)
            c.setFillColor(HexColor("#666666"))
            c.drawCentredString(width/2, 40, reshape(f"ایجاد شده در: {datetime.datetime.now().strftime('%Y/%m/%d')}"))
            c.drawCentredString(width/2, 25, reshape("نرم‌افزارهای کاربردی ویندوز | توسعه توسط Amir-Mahdi-Barati"))

            c.save()
            QMessageBox.information(self, "موفقیت", "فایل PDF با موفقیت ذخیره شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"خطا در تولید PDF: {str(e)}")

    def wrap_text(self, text, max_chars):
        """Wrap text for PDF display"""
        lines = []
        while len(text) > max_chars:
            idx = text.rfind(" ", 0, max_chars)
            if idx == -1:
                idx = max_chars
            lines.append(text[:idx].strip())
            text = text[idx:].strip()
        if text:
            lines.append(text)
        return lines or [""]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(load_qt_font())
    window = InvoiceApp()
    window.show()
    sys.exit(app.exec_())

    # By Amir Mahdi