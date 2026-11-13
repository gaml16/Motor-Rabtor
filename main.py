import flet as ft
import urllib.request
import random
import asyncio

try:
    from bleak import BleakScanner, BleakClient
    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False

BLE_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

def main(page: ft.Page):
    page.title = "Motor Rabtor - Master"
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 15

    # تهيئة الاهتزاز بأمان
    haptic = ft.HapticFeedback()
    page.overlay.append(haptic)

    mode = "NONE"
    ble_client = None
    power_on = True

    ip_box = ft.TextField(label="IP الروبوت", value="192.168.4.1", width=180, height=45)
    ble_box = ft.TextField(label="اسم البلوتوث", value="MotorRabtor", width=180, height=45)
    status = ft.Text("غير متصل", color=ft.Colors.RED_ACCENT, weight=ft.FontWeight.BOLD)

    def show_msg(text):
        try:
            page.open(ft.SnackBar(ft.Text(text), duration=600))
        except Exception:
            page.snack_bar = ft.SnackBar(ft.Text(text), duration=600)
            page.snack_bar.open = True
            page.update()

    async def set_wifi(e):
        nonlocal mode, ble_client
        if ble_client and ble_client.is_connected:
            try:
                await ble_client.disconnect()
            except Exception:
                pass
        mode = "WIFI"
        status.value = f"متصل Wi-Fi ({ip_box.value.strip()})"
        status.color = ft.Colors.GREEN_ACCENT
        page.update()

    async def set_ble(e):
        nonlocal mode, ble_client
        if not BLE_AVAILABLE:
            status.value = "مكتبة البلوتوث غير متوفرة"
            status.color = ft.Colors.ORANGE_ACCENT
            page.update()
            return

        status.value = "جاري البحث عن الروبوت..."
        status.color = ft.Colors.AMBER
        page.update()

        try:
            dev = await BleakScanner.find_device_by_name(ble_box.value.strip(), timeout=5.0)
            if dev:
                ble_client = BleakClient(dev)
                await ble_client.connect()
                mode = "BLE"
                status.value = f"متصل BLE ({dev.name})"
                status.color = ft.Colors.BLUE_ACCENT
            else:
                status.value = "الجهاز غير موجود، تأكد من تشغيله"
                status.color = ft.Colors.RED_ACCENT
        except Exception as ex:
            status.value = "فشل الاتصال: فعّل البلوتوث والموقع وأعطِ الصلاحية"
            status.color = ft.Colors.RED_ACCENT
        page.update()

    def send_http_request(url):
        try:
            urllib.request.urlopen(url, timeout=0.6)
        except Exception:
            pass

    async def send(code, label=""):
        try:
            await haptic.heavy_impact()
        except Exception:
            try:
                haptic.heavy_impact()
            except Exception:
                pass

        if mode == "WIFI":
            url = f"http://{ip_box.value.strip()}/cmd?val={code}"
            await asyncio.to_thread(send_http_request, url)
        elif mode == "BLE" and ble_client and ble_client.is_connected:
            try:
                await ble_client.write_gatt_char(BLE_UUID, code.encode())
            except Exception:
                status.value = "انقطع اتصال البلوتوث"
                status.color = ft.Colors.RED_ACCENT
                page.update()
        
        if label:
            show_msg(f"أمر: {label}")

    def btn(text, code, icon=None, color=None, w=130):
        return ft.Button(
            content=ft.Text(text),
            icon=icon,
            width=w,
            bgcolor=color,
            on_click=lambda e: page.run_task(send, code, text)
        )

    # 1. الصفحة الأولى: الحركة
    p1 = ft.Column([
        ft.Text("التحكم في الحركة", size=18, weight=ft.FontWeight.BOLD),
        btn("أمام", "F", ft.Icons.ARROW_UPWARD),
        ft.Row(
            [btn("يسار", "L", ft.Icons.ARROW_BACK), btn("يمين", "R", ft.Icons.ARROW_FORWARD)],
            alignment=ft.MainAxisAlignment.CENTER
        ),
        btn("خلف", "B", ft.Icons.ARROW_DOWNWARD),
        btn("توقف", "S", color=ft.Colors.RED_900)
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)

    # 2. الصفحة الثانية: الأوامر والصوتيات
    reply_txt = ft.Text("رد الروبوت: ...", color=ft.Colors.AMBER)
    def speak(e):
        r = random.choice(["طورني جمال وعادل وأحمد!", "تمام يا باشا", "جاهز للأوامر", "أنا سامعك"])
        reply_txt.value = f"رد الروبوت: {r}"
        page.run_task(send, "SPK", r)

    pwr_btn_text = ft.Text("إيقاف الروبوت")
    def toggle_pwr(e):
        nonlocal power_on
        power_on = not power_on
        new_label = "إيقاف الروبوت" if power_on else "تشغيل الروبوت"
        pwr_btn_text.value = new_label
        e.control.bgcolor = ft.Colors.RED_700 if power_on else ft.Colors.GREEN_700
        page.run_task(send, "ON" if power_on else "OFF", new_label)

    p2 = ft.Column([
        ft.Text("الأوامر والصوتيات", size=18, weight=ft.FontWeight.BOLD),
        btn("الكلكس", "HORN", ft.Icons.CAMPAIGN, w=240),
        btn("الميكروفون", "MIC", ft.Icons.MIC, w=240),
        ft.Button(content=ft.Text("الإسبيكر (رد الروبوت)"), icon=ft.Icons.VOLUME_UP, width=240, on_click=speak),
        reply_txt,
        btn("الضوء", "LIGHT", ft.Icons.LIGHTBULB, w=240),
        ft.Button(
            content=pwr_btn_text,
            icon=ft.Icons.POWER_SETTINGS_NEW,
            width=240,
            bgcolor=ft.Colors.RED_700,
            on_click=toggle_pwr
        )
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    # 3. الصفحة الثالثة: الأطراف
    p3 = ft.Column([
        ft.Text("التحكم في الأطراف", size=18, weight=ft.FontWeight.BOLD),
        ft.Text("الرأس"),
        ft.Row([btn("رأس شمال", "HL"), btn("رأس يمين", "HR")], alignment=ft.MainAxisAlignment.CENTER),
        ft.Text("اليد اليمنى"),
        ft.Row([btn("يمنى فوق", "RU"), btn("يمنى تحت", "RD")], alignment=ft.MainAxisAlignment.CENTER),
        ft.Text("اليد اليسرى"),
        ft.Row([btn("يسرى فوق", "LU"), btn("يسرى تحت", "LD")], alignment=ft.MainAxisAlignment.CENTER),
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

    # 4. الصفحة الرابعة: الرادار الذكي
    radar_status = ft.Text("جاري فحص المسار...", size=16, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)
    dist_txt = ft.Text("المسافة: -- سم",
    
