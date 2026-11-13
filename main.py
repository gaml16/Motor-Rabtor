import flet as ft
import urllib.request
import random
import asyncio

# محاولة استيراد مكتبة البلوتوث بأمان لتفادي توقف التطبيق إذا لم تكن مثبتة
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
    page.padding = 15

    # الاهتزاز عند الضغط (مع حماية في حال عدم دعم الجهاز)
    haptic = ft.HapticFeedback()
    page.overlay.append(haptic)

    mode = "NONE"
    ble_client = None
    power_on = True

    ip_box = ft.TextField(label="IP الروبوت", value="192.168.4.1", width=180, height=45)
    ble_box = ft.TextField(label="اسم البلوتوث", value="MotorRabtor", width=180, height=45)
    status = ft.Text("غير متصل", color=ft.Colors.RED_ACCENT, weight=ft.FontWeight.BOLD)

    async def set_wifi(e):
        nonlocal mode, ble_client
        if ble_client and ble_client.is_connected:
            try:
                await ble_client.disconnect()
            except Exception:
                pass
        mode = "WIFI"
        status.value = f"متصل Wi-Fi ({ip_box.value})"
        status.color = ft.Colors.GREEN_ACCENT
        page.update()

    async def set_ble(e):
        nonlocal mode, ble_client
        if not BLE_AVAILABLE:
            status.value = "البلوتوث يتطلب بناء التطبيق كـ APK"
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
        except Exception:
            status.value = "فشل الاتصال، فعّل البلوتوث والموقع (GPS)"
            status.color = ft.Colors.RED_ACCENT
        page.update()

    def send_http_request(url):
        try:
            urllib.request.urlopen(url, timeout=0.6)
        except Exception:
            pass

    async def send(code, label=""):
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
            page.snack_bar = ft.SnackBar(ft.Text(f"أمر: {label}"), duration=500)
            page.snack_bar.open = True
            page.update()

    def btn(text, code, icon=None, color=None, w=130):
        return ft.Button(
            text,
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

    def toggle_pwr(e):
        nonlocal power_on
        power_on = not power_on
        new_label = "إيقاف الروبوت" if power_on else "تشغيل الروبوت"
        e.control.text = new_label
        e.control.bgcolor = ft.Colors.RED_700 if power_on else ft.Colors.GREEN_700
        page.run_task(send, "ON" if power_on else "OFF", new_label)

    p2 = ft.Column([
        ft.Text("الأوامر والصوتيات", size=18, weight=ft.FontWeight.BOLD),
        btn("الكلكس", "HORN", ft.Icons.CAMPAIGN, w=240),
        btn("الميكروفون", "MIC", ft.Icons.MIC, w=240),
        ft.Button("الإسبيكر (رد الروبوت)", icon=ft.Icons.VOLUME_UP, width=240, on_click=speak),
        reply_txt,
        btn("الضوء", "LIGHT", ft.Icons.LIGHTBULB, w=240),
        ft.Button(
            "إيقاف الروبوت",
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
    dist_txt = ft.Text("المسافة: -- سم", size=14, color=ft.Colors.CYAN_200)
    
    radar_box = ft.Container(
        width=260,
        height=180,
        bgcolor=ft.Colors.GREEN_900,
        border_radius=16,
        alignment=ft.alignment.center,
        padding=10,
        content=ft.Column(
            [radar_status, dist_txt],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

    def update_radar_ui(distance):
        dist_txt.value = f"المسافة الحالية: {distance:.1f} سم"
        if distance <= 15.0:
            radar_box.bgcolor = ft.Colors.RED_900
            radar_status.value = "🚨 تحذير: عائق ضخم وقريب جداً!"
            try:
                haptic.heavy_impact()
            except Exception:
                pass
        elif distance <= 40.0:
            radar_box.bgcolor = ft.Colors.ORANGE_900
            radar_status.value = "⚠️ انتبه: عائق بسيط أمام الروبوت"
        else:
            radar_box.bgcolor = ft.Colors.GREEN_900
            radar_status.value = "✅ المسار سالك وآمن تماماً"
        page.update()

    current_test_dist = 60.0
    def cycle_test_radar(e):
        nonlocal current_test_dist
        if current_test_dist > 40.0:
            current_test_dist = 28.0
        elif current_test_dist > 20.0:
            current_test_dist = 11.5
        else:
            current_test_dist = 75.0
        update_radar_ui(current_test_dist)

    p4 = ft.Column([
        ft.Text("الرادار وكشف العوائق", size=18, weight=ft.FontWeight.BOLD),
        radar_box,
        ft.Row([btn("رادار شمال", "RL"), btn("رادار يمين", "RR")], alignment=ft.MainAxisAlignment.CENTER),
        ft.Button("فحص وتجربة حساسية الرادار", icon=ft.Icons.SENSORS, on_click=cycle_test_radar)
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)

    header = ft.Column([
        ft.Row([ip_box, ft.IconButton(ft.Icons.WIFI, on_click=lambda e: page.run_task(set_wifi, e))], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([ble_box, ft.IconButton(ft.Icons.BLUETOOTH, on_click=lambda e: page.run_task(set_ble, e))], alignment=ft.MainAxisAlignment.CENTER),
        status
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)

    pages = [p1, p2, p3, p4]
    body = ft.Container(content=pages[0], expand=True, padding=10)

    def change_tab(e):
        body.content = pages[e.control.selected_index]
        page.update()

    page.navigation_bar = ft.NavigationBar(
        on_change=change_tab,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.GAMEPAD, label="الحركة"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_VOICE, label="الأوامر"),
            ft.NavigationBarDestination(icon=ft.Icons.ACCESSIBILITY_NEW, label="الأطراف"),
            ft.NavigationBarDestination(icon=ft.Icons.RADAR, label="الرادار"),
        ]
    )

    page.add(header, body)

if __name__ == "__main__":
    ft.run(main)
      
