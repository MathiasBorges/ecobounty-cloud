"""Tela de Câmera, Scanner e Auditoria por IA (UC08, UC09, UC10)."""
import inspect
import threading
import time
from pathlib import Path
from typing import Callable, Optional
import flet as ft

from app.config import DEFAULT_USER_LAT, DEFAULT_USER_LNG
from app.models.bounty import Bounty
from app.models.user import User
from app.services.bounty_service import BountyService
from app.services.storage_service import StorageService, get_storage_service, start_upload_server


class CameraView(ft.UserControl):
    def __init__(
        self,
        mode: str,  # "phase1", "phase2", "denuncia"
        user: User,
        bounty_service: BountyService,
        bounty: Optional[Bounty] = None,
        storage_service: Optional[StorageService] = None,
        auto_open: bool = False,
        user_lat: float = DEFAULT_USER_LAT,
        user_lng: float = DEFAULT_USER_LNG,
        captured_image_path: Optional[str] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        on_success_phase1: Optional[Callable[..., None]] = None,
        on_success_phase2: Optional[Callable[[float], None]] = None,
        on_success_denuncia: Optional[Callable[[Bounty], None]] = None,
    ):
        super().__init__()
        self.mode = mode
        self.user = user
        self.bounty_service = bounty_service
        self.bounty = bounty
        self.storage_service = storage_service or get_storage_service()
        self.auto_open = auto_open
        self.user_lat = user_lat
        self.user_lng = user_lng
        self.on_cancel = on_cancel
        self.on_success_phase1 = on_success_phase1
        self.on_success_phase2 = on_success_phase2
        self.on_success_denuncia = on_success_denuncia

        self.is_processing = False
        self.is_uploading = False
        self.captured_image_path: Optional[str] = captured_image_path
        self.error_text = ft.Text("", color="#ef4444", size=13, weight=ft.FontWeight.BOLD, visible=False)

        # FilePicker para captura real pelo dispositivo / galeria / câmera nativa
        self.file_picker = ft.FilePicker(
            on_result=self.on_file_picker_result,
            on_upload=self.on_file_picker_upload,
        )

        # Modos de simulação para testes
        self.simulate_phase1_failure = False
        self.simulate_denuncia_mode = "valid"  # "valid", "empty", "duplicate"
        dest_name = self.bounty.dest if self.bounty else "COOPLUM"
        self.selected_qr_code = f"ECOPONTO-{dest_name}-001"

        self.root_container = ft.Container(expand=True, bgcolor="#020617")

    def did_mount(self):
        if self.page and self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)
            self.page.update()

    def safe_update(self):
        if self.page:
            self.update()

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if not e.files:
            return
        f = e.files[0]
        if getattr(f, "path", None):
            # Execução local / desktop: caminho físico direto no SO
            try:
                saved = self.storage_service.save_image_from_file(f.path)
                self.captured_image_path = saved
                self.is_uploading = False
                self.error_text.visible = False
                self._render()
                self.safe_update()
            except Exception as exc:
                self.is_uploading = False
                self.error_text.value = f"Erro ao importar foto: {exc}"
                self.error_text.visible = True
                self.safe_update()
        else:
            # Execução Web / Celular: realiza upload via servidor Flet para persistência física
            try:
                self.is_uploading = True
                self.error_text.visible = False
                self._render()
                self.safe_update()
                upload_url = self.page.get_upload_url(f.name, 600)
                self.file_picker.upload([ft.FilePickerUploadFile(f.name, upload_url=upload_url)])
            except Exception:
                self.is_uploading = False
                saved = self.storage_service.create_sample_photo(
                    label="Lixo Detectado" if self.mode == "denuncia" else "Área Limpa",
                    is_clean=(self.mode == "phase1"),
                )
                self.captured_image_path = saved
                self.error_text.visible = False
                self._render()
                self.safe_update()

    def on_file_picker_upload(self, e: ft.FilePickerUploadEvent):
        if e.error:
            self.is_uploading = False
            self.error_text.value = f"Erro ao enviar foto: {e.error}"
            self.error_text.visible = True
            self._render()
            self.safe_update()
        elif e.progress == 1.0:
            self.is_uploading = False
            # Flet grava em UPLOADS_DIR / e.file_name. Garante persistência permanente com UUID.
            try:
                phys_path = self.storage_service.get_physical_path(e.file_name)
                if phys_path.exists():
                    saved = self.storage_service.save_image_from_file(phys_path)
                    self.captured_image_path = saved
                    if phys_path.name != Path(saved).name:
                        try:
                            phys_path.unlink()
                        except Exception:
                            pass
                else:
                    self.captured_image_path = f"/uploads/{e.file_name}"
            except Exception:
                self.captured_image_path = f"/uploads/{e.file_name}"

            self.error_text.visible = False
            self._render()
            self.safe_update()

    def open_camera_picker(self, e=None):
        """Abre o seletor nativo de câmera / arquivos do dispositivo com feedback visual imediato."""
        if not self.page:
            saved = self.storage_service.create_sample_photo(
                label="Lixo Detectado" if self.mode == "denuncia" else "Área Limpa",
                is_clean=(self.mode == "phase1"),
            )
            self.captured_image_path = saved
            self.error_text.visible = False
            self._render()
            return

        if self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)

        # Feedback visual imediato para o usuário
        self.page.snack_bar = ft.SnackBar(
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.icons.PHOTO_CAMERA, color="white", size=18),
                    ft.Text("Seletor aberto: tire a foto ou escolha um arquivo (ou use 'Foto Teste').", size=12),
                ],
            ),
            bgcolor="#0284c7",
            duration=3000,
        )
        self.page.snack_bar.open = True
        self.page.update()

        try:
            self.file_picker.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.IMAGE,
                dialog_title="Capturar Foto com a Câmera ou Selecionar Imagem",
            )
        except Exception:
            pass

    def open_realtime_camera(self, e=None):
        """Abre o visor de câmera em tempo real integrado na mesma página (sem abrir nova aba)."""
        start_upload_server()
        from app.services.storage_service import get_client_id, register_photo_listener, set_pending_action
        cid = get_client_id(self.page)
        set_pending_action("open_camera", {"mode": self.mode, "user_id": self.user.id if self.user else ""}, cid=cid)
        register_photo_listener(self.on_photo_uploaded_from_in_page, cid=cid)

        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.icons.VIDEOCAM, color="white", size=18),
                        ft.Text("Visor da câmera aberto na tela! Aponte e fotografe."),
                    ],
                ),
                bgcolor="#059669",
                duration=3000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def on_photo_uploaded_from_in_page(self, saved_path: str):
        """Callback acionado instantaneamente quando o usuário fotografa na mesma página."""
        from app.services.storage_service import unregister_photo_listener
        unregister_photo_listener(self.on_photo_uploaded_from_in_page)
        self.captured_image_path = saved_path
        self.error_text.visible = False
        self._render()
        self.safe_update()
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                        ft.Text("Foto capturada e salva com sucesso!"),
                    ],
                ),
                bgcolor="#059669",
                duration=2000,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def will_unmount(self):
        from app.services.storage_service import unregister_photo_listener
        unregister_photo_listener(self.on_photo_uploaded_from_in_page)

    def capture_webcam(self, e=None):
        """Captura foto real da webcam física usando OpenCV se disponível."""
        try:
            import importlib
            cv2 = importlib.import_module("cv2")
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                cap = cv2.VideoCapture(1)

            if not cap.isOpened():
                if self.page:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.icons.INFO, color="white", size=18),
                                ft.Text("Webcam direta indisponível. Abrindo seletor de câmera do dispositivo..."),
                            ],
                        ),
                        bgcolor="#0284c7",
                        duration=2500,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                self.open_camera_picker(e)
                return

            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                if self.page:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Row(
                            spacing=8,
                            controls=[
                                ft.Icon(ft.icons.INFO, color="white", size=18),
                                ft.Text("Webcam direta indisponível. Abrindo seletor de câmera do dispositivo..."),
                            ],
                        ),
                        bgcolor="#0284c7",
                        duration=2500,
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
                self.open_camera_picker(e)
                return

            _, buf = cv2.imencode(".jpg", frame)
            saved = self.storage_service.save_image(buf.tobytes(), "jpg")
            self.captured_image_path = saved
            self.error_text.visible = False
            self._render()
            self.safe_update()
            if self.page:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Row(
                        spacing=8,
                        controls=[
                            ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                            ft.Text("Foto da webcam capturada e salva com sucesso!"),
                        ],
                    ),
                    bgcolor="#059669",
                    duration=2500,
                )
                self.page.snack_bar.open = True
                self.page.update()
        except Exception:
            self.open_camera_picker(e)

    def take_instant_photo(self, e=None):
        """Gera e salva foto real com geolocalização e carimbo de tempo para simulações e testes."""
        saved = self.storage_service.create_sample_photo(
            label="Lixo Detectado" if self.mode == "denuncia" else "Área Limpa",
            lat=self.user_lat,
            lng=self.user_lng,
            is_clean=(self.mode == "phase1"),
        )
        self.captured_image_path = saved
        self.error_text.visible = False
        self._render()
        self.safe_update()
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Row(
                    spacing=8,
                    controls=[
                        ft.Icon(ft.icons.CHECK_CIRCLE, color="white", size=18),
                        ft.Text("Foto de teste gerada e armazenada em app/assets/uploads/!"),
                    ],
                ),
                bgcolor="#059669",
                duration=2500,
            )
            self.page.snack_bar.open = True
            self.page.update()

    def clear_captured_photo(self, e=None):
        """Descarta a foto atual para capturar outra."""
        self.captured_image_path = None
        self.error_text.visible = False
        self._render()
        self.safe_update()

    def set_phase1_simulation(self, failure: bool, e=None):
        self.simulate_phase1_failure = failure
        self.error_text.visible = False
        self._render()
        self.safe_update()

    def set_denuncia_simulation(self, mode: str, e=None):
        self.simulate_denuncia_mode = mode
        self.error_text.visible = False
        self._render()
        self.safe_update()

    def set_test_qr(self, qr_val: str, e=None):
        self.selected_qr_code = qr_val
        self.error_text.visible = False
        self._render()
        self.safe_update()

    def handle_shutter_click(self, e):
        if self.is_processing:
            # Impede clique duplo / concorrência (UC08 FE1)
            return

        # Se ainda não houver foto capturada nos modos fotográficos:
        if not self.captured_image_path and self.mode in ("denuncia", "phase1"):
            is_explicit_sim = (
                self.simulate_phase1_failure
                or self.simulate_denuncia_mode in ("empty", "duplicate")
            )
            # Na execução real com página ativa e sem simulação de erro, aciona a câmera real
            if self.page and not is_explicit_sim:
                if hasattr(self.page, "launch_url"):
                    self.open_realtime_camera(e)
                else:
                    self.open_camera_picker(e)
                return
            else:
                # Fallback para testes automatizados headless
                self.captured_image_path = self.storage_service.create_sample_photo(
                    label="Lixo Detectado" if self.mode == "denuncia" else "Área Limpa",
                    lat=self.user_lat,
                    lng=self.user_lng,
                    is_clean=(self.mode == "phase1"),
                )

        self.is_processing = True
        self.error_text.visible = False
        self._render()
        self.safe_update()

        def background_inference():
            try:
                time.sleep(0.5)  # Simula tempo de inferência da IA

                if self.mode == "denuncia":
                    from app.services.geo_service import get_geo_service
                    geo = get_geo_service()
                    if geo.is_real_location:
                        lat_to_use = geo.user_lat
                        lng_to_use = geo.user_lng
                    elif self.user_lat != DEFAULT_USER_LAT or self.user_lng != DEFAULT_USER_LNG:
                        lat_to_use = self.user_lat
                        lng_to_use = self.user_lng
                    else:
                        lat_to_use = geo.user_lat
                        lng_to_use = geo.user_lng

                    if self.simulate_denuncia_mode == "empty":
                        ok, new_bounty, msg = self.bounty_service.create_denuncia_bounty(
                            user_id=self.user.id,
                            lat=lat_to_use,
                            lng=lng_to_use,
                            simulate_empty=True,
                        )
                    elif self.simulate_denuncia_mode == "duplicate":
                        ok, new_bounty, msg = self.bounty_service.create_denuncia_bounty(
                            user_id=self.user.id,
                            lat=-9.6621,
                            lng=-35.7301,
                        )
                    else:
                        img_to_send = self.captured_image_path or "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80"
                        ok, new_bounty, msg = self.bounty_service.create_denuncia_bounty(
                            user_id=self.user.id,
                            lat=lat_to_use,
                            lng=lng_to_use,
                            image_data=img_to_send,
                        )

                    self.is_processing = False
                    if ok and self.on_success_denuncia:
                        self.on_success_denuncia(new_bounty)
                    else:
                        self.error_text.value = msg
                        self.error_text.visible = True
                        self._render()
                        self.safe_update()

                elif self.mode == "phase1" and self.bounty:
                    ok, half_val, msg = self.bounty_service.validate_phase1_cleaning(
                        bounty_id=self.bounty.id,
                        user_id=self.user.id,
                        image_data=self.captured_image_path,
                        simulate_failure=self.simulate_phase1_failure,
                    )
                    self.is_processing = False
                    if ok and self.on_success_phase1:
                        try:
                            sig = inspect.signature(self.on_success_phase1)
                            if len(sig.parameters) >= 2:
                                self.on_success_phase1(half_val, self.captured_image_path)
                            else:
                                self.on_success_phase1(half_val)
                        except Exception:
                            self.on_success_phase1(half_val)
                    else:
                        self.error_text.value = msg
                        self.error_text.visible = True
                        self._render()
                        self.safe_update()

                elif self.mode == "phase2" and self.bounty:
                    ok, rem_val, msg = self.bounty_service.validate_phase2_ecopoint(
                        bounty_id=self.bounty.id,
                        user_id=self.user.id,
                        qrcode_data=self.selected_qr_code,
                        image_data=self.captured_image_path,
                    )
                    self.is_processing = False
                    if ok and self.on_success_phase2:
                        self.on_success_phase2(rem_val)
                    else:
                        self.error_text.value = msg
                        self.error_text.visible = True
                        self._render()
                        self.safe_update()
            except Exception:
                self.is_processing = False

        self.current_thread = threading.Thread(target=background_inference, daemon=True)
        self.current_thread.start()

    def build(self):
        self._render()
        return self.root_container

    def _render(self):
        # Instruções e mensagens
        if self.mode == "phase1":
            instruction_text = "Enquadre a área LIMPA (auditoria de coleta)"
            proc_text = "IA analisando a limpeza da área..."
        elif self.mode == "phase2":
            instruction_text = "Fotografe o descarte no Ecoponto / Lixeira"
            proc_text = "Validando comprovante de descarte..."
        else:
            instruction_text = "Fotografe o lixo irregular para criar a missão"
            proc_text = "Mapeando e gerando Bounty..."

        # Header Superior
        header = ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.IconButton(
                        icon=ft.icons.CLOSE,
                        icon_color="white",
                        bgcolor="#334155",
                        tooltip="Cancelar",
                        on_click=lambda e: self.on_cancel() if self.on_cancel else None,
                    ),
                    # Indicador REC
                    ft.Container(
                        bgcolor="#dc2626",
                        padding=ft.padding.symmetric(horizontal=10, vertical=4),
                        border_radius=12,
                        content=ft.Row(
                            spacing=6,
                            controls=[
                                ft.Container(width=8, height=8, border_radius=4, bgcolor="white"),
                                ft.Text("REC", color="white", weight=ft.FontWeight.BOLD, size=11),
                            ],
                        ),
                    ),
                ],
            ),
        )

        # Visor Central (Enquadramento de Câmera ou Preview da Foto Capturada)
        if self.is_processing:
            viewfinder_content = ft.Container(
                alignment=ft.alignment.center,
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    controls=[
                        ft.ProgressRing(color="#10b981", stroke_width=4, width=54, height=54),
                        ft.Text(
                            proc_text,
                            color="#34d399",
                            weight=ft.FontWeight.BOLD,
                            size=14,
                        ),
                    ],
                ),
            )
        elif self.is_uploading:
            viewfinder_content = ft.Container(
                alignment=ft.alignment.center,
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=16,
                    controls=[
                        ft.ProgressRing(color="#34d399", stroke_width=4, width=54, height=54),
                        ft.Text(
                            "Carregando foto e armazenando...",
                            color="#34d399",
                            weight=ft.FontWeight.BOLD,
                            size=14,
                        ),
                    ],
                ),
            )
        elif self.captured_image_path and self.mode != "phase2":
            from app.services.storage_service import get_image_base64
            cam_b64 = get_image_base64(self.captured_image_path)
            # Exibe a foto real capturada e salva
            viewfinder_content = ft.Container(
                expand=True,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                border_radius=18,
                content=ft.Stack(
                    controls=[
                        ft.Image(
                            src=self.captured_image_path if not cam_b64 else None,
                            src_base64=cam_b64,
                            fit=ft.ImageFit.COVER,
                            expand=True,
                            width=400,
                            height=360,
                        ),
                        ft.Container(
                            top=12,
                            left=12,
                            bgcolor="rgba(15, 23, 42, 0.85)",
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=12,
                            content=ft.Row(
                                tight=True,
                                spacing=6,
                                controls=[
                                    ft.Icon(ft.icons.CHECK_CIRCLE, color="#34d399", size=15),
                                    ft.Text("Foto Salva em uploads/", color="white", size=11, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                        ),
                        ft.Container(
                            bottom=12,
                            alignment=ft.alignment.center,
                            content=ft.ElevatedButton(
                                content=ft.Row(
                                    tight=True,
                                    spacing=6,
                                    controls=[
                                        ft.Icon(ft.icons.REFRESH, color="#1e293b", size=16),
                                        ft.Text("Tirar Outra Foto", color="#1e293b", size=12, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                bgcolor="white",
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=20)),
                                on_click=self.clear_captured_photo,
                            ),
                        ),
                    ]
                ),
            )
        else:
            # Modo visor com ações claras e proeminentes para acionar a câmera real
            viewfinder_content = ft.Container(
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(horizontal=16, vertical=16),
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                    controls=[
                        ft.Icon(
                            ft.icons.PHOTO_CAMERA if self.mode == "phase2" else ft.icons.CAMERA_ALT,
                            color="#34d399",
                            size=64,
                        ),
                        ft.Text(
                            "Toque para Fotografar o Descarte" if self.mode == "phase2" else "Toque para Abrir a Câmera",
                            color="white",
                            weight=ft.FontWeight.BOLD,
                            size=16,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            instruction_text,
                            color="#cbd5e1",
                            weight=ft.FontWeight.W_500,
                            size=13,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        *(
                            [
                                ft.Container(height=4),
                                # Botão Principal Proeminente: Câmera em Tempo Real (com permissão)
                                ft.ElevatedButton(
                                    content=ft.Row(
                                        tight=True,
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.icons.VIDEOCAM, size=20, color="white"),
                                            ft.Text("Abrir Câmera em Tempo Real", size=14, color="white", weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                    bgcolor="#059669",
                                    style=ft.ButtonStyle(
                                        shape=ft.RoundedRectangleBorder(radius=12),
                                        padding=ft.padding.symmetric(horizontal=24, vertical=16),
                                    ),
                                    on_click=self.open_realtime_camera,
                                ),
                                ft.Container(height=4),
                                # Opções secundárias: Webcam PC, Importar Arquivo e Foto Teste
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=8,
                                    controls=[
                                        ft.TextButton(
                                            content=ft.Row(
                                                tight=True,
                                                spacing=4,
                                                controls=[
                                                    ft.Icon(ft.icons.PHOTO_CAMERA, size=14, color="#94a3b8"),
                                                    ft.Text("Webcam Direta", size=11, color="#94a3b8"),
                                                ],
                                            ),
                                            on_click=self.capture_webcam,
                                        ),
                                        ft.Text("•", color="#64748b", size=12),
                                        ft.TextButton(
                                            content=ft.Row(
                                                tight=True,
                                                spacing=4,
                                                controls=[
                                                    ft.Icon(ft.icons.FOLDER, size=14, color="#94a3b8"),
                                                    ft.Text("Galeria / Arquivo", size=11, color="#94a3b8"),
                                                ],
                                            ),
                                            on_click=self.open_camera_picker,
                                        ),
                                        ft.Text("•", color="#64748b", size=12),
                                        ft.TextButton(
                                            content=ft.Row(
                                                tight=True,
                                                spacing=4,
                                                controls=[
                                                    ft.Icon(ft.icons.BOLT, size=14, color="#f59e0b"),
                                                    ft.Text("Foto Teste", size=11, color="#f59e0b"),
                                                ],
                                            ),
                                            on_click=self.take_instant_photo,
                                        ),
                                    ],
                                ),
                            ]
                            if self.mode != "phase2"
                            else []
                        ),
                    ],
                ),
            )

        # O visor central inteiro é interativo quando não há foto carregada
        viewfinder_box = ft.Container(
            expand=True,
            margin=ft.margin.symmetric(horizontal=24, vertical=12),
            border_radius=20,
            border=ft.border.all(2, "#059669" if not self.is_processing else "#10b981"),
            bgcolor="#090d16",
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=20, color="#059669"),
            on_click=self.open_realtime_camera if not self.captured_image_path and self.mode != "phase2" else None,
            content=ft.Stack(
                controls=[
                    # Linha do Scanner (animada quando em processamento)
                    ft.Container(
                        height=3,
                        bgcolor="#34d399",
                        shadow=ft.BoxShadow(spread_radius=2, blur_radius=8, color="#34d399"),
                        visible=self.is_processing,
                    ),
                    viewfinder_content,
                ],
            ),
        )

        # Seletor de Simulação conforme o Modo
        simulation_bar = ft.Container()
        if not self.is_processing:
            if self.mode == "phase1":
                simulation_bar = ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=4),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Text("Simular Foto:", color="#94a3b8", size=11),
                            ft.TextButton(
                                "Área Limpa (Aprovar)",
                                style=ft.ButtonStyle(
                                    color="#34d399" if not self.simulate_phase1_failure else "#64748b"
                                ),
                                on_click=lambda e: self.set_phase1_simulation(False, e),
                            ),
                            ft.TextButton(
                                "Resíduo Visível (Reprovar)",
                                style=ft.ButtonStyle(
                                    color="#ef4444" if self.simulate_phase1_failure else "#64748b"
                                ),
                                on_click=lambda e: self.set_phase1_simulation(True, e),
                            ),
                        ],
                    ),
                )
            elif self.mode == "phase2":
                dest_name = self.bounty.dest if self.bounty else "COOPLUM"
                simulation_bar = ft.Container(
                    padding=ft.padding.symmetric(horizontal=16, vertical=4),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6,
                        controls=[
                            ft.Text("Simular QR:", color="#94a3b8", size=11),
                            ft.TextButton(
                                f"Válido ({dest_name})",
                                style=ft.ButtonStyle(
                                    color="#34d399" if "DIVERGENTE" not in self.selected_qr_code else "#64748b"
                                ),
                                on_click=lambda e: self.set_test_qr(f"ECOPONTO-{dest_name}-001", e),
                            ),
                            ft.TextButton(
                                "Divergente (Erro)",
                                style=ft.ButtonStyle(
                                    color="#ef4444" if "DIVERGENTE" in self.selected_qr_code else "#64748b"
                                ),
                                on_click=lambda e: self.set_test_qr("ECOPONTO-DIVERGENTE-999", e),
                            ),
                        ],
                    ),
                )
            elif self.mode == "denuncia":
                simulation_bar = ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=4),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=4,
                        controls=[
                            ft.Text("Simular:", color="#94a3b8", size=11),
                            ft.TextButton(
                                "Com Resíduo",
                                style=ft.ButtonStyle(
                                    color="#34d399" if self.simulate_denuncia_mode == "valid" else "#64748b"
                                ),
                                on_click=lambda e: self.set_denuncia_simulation("valid", e),
                            ),
                            ft.TextButton(
                                "Sem Resíduo",
                                style=ft.ButtonStyle(
                                    color="#ef4444" if self.simulate_denuncia_mode == "empty" else "#64748b"
                                ),
                                on_click=lambda e: self.set_denuncia_simulation("empty", e),
                            ),
                            ft.TextButton(
                                "Duplicado",
                                style=ft.ButtonStyle(
                                    color="#f59e0b" if self.simulate_denuncia_mode == "duplicate" else "#64748b"
                                ),
                                on_click=lambda e: self.set_denuncia_simulation("duplicate", e),
                            ),
                        ],
                    ),
                )

        # Botão Obturador Inferior Inteligente
        has_photo = bool(self.captured_image_path)
        shutter_bgcolor = "#059669" if has_photo else ("#ffffff" if not self.is_processing else "#475569")
        shutter_icon_color = "#ffffff" if has_photo else "#059669"
        shutter_icon = ft.icons.CHECK if has_photo else (ft.icons.PHOTO_CAMERA if self.mode != "phase2" else ft.icons.QR_CODE_SCANNER)
        shutter_label = (
            "Toque para confirmar e validar missão"
            if has_photo
            else ("Toque para abrir a câmera e fotografar" if self.mode != "phase2" else "Toque para validar QR Code")
        )

        shutter_button = ft.Container(
            padding=ft.padding.only(bottom=28, top=6),
            alignment=ft.alignment.center,
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    self.error_text,
                    ft.Container(
                        on_click=self.handle_shutter_click,
                        width=76,
                        height=76,
                        border_radius=38,
                        bgcolor=shutter_bgcolor,
                        border=ft.border.all(4, "#059669"),
                        opacity=0.5 if self.is_processing else 1.0,
                        shadow=ft.BoxShadow(spread_radius=2, blur_radius=12, color="#059669")
                        if not self.is_processing
                        else None,
                        alignment=ft.alignment.center,
                        content=ft.Container(
                            width=60,
                            height=60,
                            border_radius=30,
                            border=ft.border.all(1, "#cbd5e1" if not has_photo else "#34d399"),
                            alignment=ft.alignment.center,
                            content=ft.Icon(
                                shutter_icon,
                                color=shutter_icon_color,
                                size=28,
                            ),
                        ),
                    ),
                    ft.Text(
                        shutter_label,
                        color="#94a3b8",
                        size=11,
                        weight=ft.FontWeight.W_500,
                    ),
                ],
            ),
        )

        self.root_container.content = ft.Column(
            spacing=0,
            controls=[
                header,
                viewfinder_box,
                simulation_bar,
                shutter_button,
            ],
        )
