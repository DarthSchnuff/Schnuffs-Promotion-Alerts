"""
Universal StreamDeck Manager für SchnuffsPromotionAlerts
Unterstützt: Elgato Stream Deck, VSDinside Stream Dock, Software-Alternativen

Installation:
pip install streamdeck pillow websocket-client

Author: SchnuffsPromotionAlerts
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from PIL import Image, ImageDraw, ImageFont
import threading
import json
import logging
from typing import Callable, Optional, Dict, List, Tuple
from pathlib import Path

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseDeckController(ABC):
    """
    Abstrakte Basisklasse für alle Deck-Controller
    Jeder Hersteller implementiert diese Interface
    """
    
    def __init__(self):
        self.connected = False
        self.key_count = 0
        self.key_callback = None
        
    @abstractmethod
    def initialize(self) -> bool:
        """Initialisiert die Verbindung zum Deck"""
        pass
    
    @abstractmethod
    def set_key_image(self, key: int, image_data: bytes):
        """Setzt das Bild für einen Key"""
        pass
    
    @abstractmethod
    def set_brightness(self, percent: int):
        """Setzt die Helligkeit (0-100)"""
        pass
    
    @abstractmethod
    def reset(self):
        """Resettet das Deck (alle LEDs aus)"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """Räumt auf und schließt Verbindung"""
        pass
    
    def register_key_callback(self, callback: Callable[[int, bool], None]):
        """Registriert Callback für Key-Events"""
        self.key_callback = callback


class ElgatoStreamDeckController(BaseDeckController):
    """
    Controller für Elgato Stream Deck (Mini, MK.2, XL, Plus)
    """
    
    def __init__(self):
        super().__init__()
        self.deck = None
        
    def initialize(self) -> bool:
        """Initialisiert Elgato Stream Deck"""
        try:
            from StreamDeck.DeviceManager import DeviceManager
            from StreamDeck.ImageHelpers import PILHelper
            
            self.PILHelper = PILHelper
            
            streamdecks = DeviceManager().enumerate()
            
            if len(streamdecks) == 0:
                logger.warning("Kein Elgato Stream Deck gefunden")
                return False
            
            self.deck = streamdecks[0]
            self.deck.open()
            self.deck.reset()
            
            self.key_count = self.deck.key_count()
            self.connected = True
            
            # Callback registrieren
            self.deck.set_key_callback(self._key_callback_wrapper)
            
            logger.info(f"✅ Elgato Stream Deck verbunden: {self.deck.deck_type()}")
            logger.info(f"📊 Tasten: {self.key_count}")
            
            return True
            
        except ImportError:
            logger.error("StreamDeck Library nicht installiert! pip install streamdeck")
            return False
        except Exception as e:
            logger.error(f"Fehler bei Elgato Initialisierung: {e}")
            return False
    
    def _key_callback_wrapper(self, deck, key, state):
        """Wrapper für Elgato Callback"""
        if self.key_callback:
            self.key_callback(key, state)
    
    def set_key_image(self, key: int, image_data: bytes):
        """Setzt Key-Bild für Elgato"""
        try:
            if self.deck and 0 <= key < self.key_count:
                self.deck.set_key_image(key, image_data)
        except Exception as e:
            logger.error(f"Fehler beim Setzen von Key {key}: {e}")
    
    def set_brightness(self, percent: int):
        """Setzt Helligkeit (0-100)"""
        try:
            if self.deck:
                self.deck.set_brightness(percent)
        except Exception as e:
            logger.error(f"Fehler beim Setzen der Helligkeit: {e}")
    
    def reset(self):
        """Resettet Deck"""
        try:
            if self.deck:
                self.deck.reset()
        except Exception as e:
            logger.error(f"Fehler beim Reset: {e}")
    
    def cleanup(self):
        """Cleanup"""
        try:
            if self.deck:
                self.deck.reset()
                self.deck.close()
                self.connected = False
                logger.info("✅ Elgato Stream Deck getrennt")
        except Exception as e:
            logger.error(f"Fehler beim Cleanup: {e}")


class VSDinsideStreamDockController(BaseDeckController):
    """
    Controller für VSDinside Stream Dock (M18, N4 Pro)
    Nutzt WebSocket-basierte Kommunikation
    """
    
    def __init__(self):
        super().__init__()
        self.ws = None
        self.ws_thread = None
        self.running = False
        
    def initialize(self) -> bool:
        """Initialisiert VSDinside Stream Dock"""
        try:
            import websocket
            
            # VSDinside nutzt WebSocket auf Port 28492 (Standard)
            ws_url = "ws://localhost:28492"
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            # WebSocket in separatem Thread starten
            self.running = True
            self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
            self.ws_thread.start()
            
            # Warte kurz auf Verbindung
            import time
            time.sleep(1)
            
            if self.connected:
                logger.info("✅ VSDinside Stream Dock verbunden")
                return True
            else:
                logger.warning("VSDinside Stream Dock nicht gefunden")
                return False
                
        except ImportError:
            logger.error("websocket-client nicht installiert! pip install websocket-client")
            return False
        except Exception as e:
            logger.error(f"Fehler bei VSDinside Initialisierung: {e}")
            return False
    
    def _run_websocket(self):
        """Führt WebSocket in Thread aus"""
        try:
            self.ws.run_forever()
        except Exception as e:
            logger.error(f"WebSocket Fehler: {e}")
    
    def _on_open(self, ws):
        """WebSocket verbunden"""
        self.connected = True
        # Info vom Gerät anfordern
        self._send_message({"event": "getInfo"})
    
    def _on_message(self, ws, message):
        """WebSocket Nachricht empfangen"""
        try:
            data = json.loads(message)
            
            if data.get("event") == "keyPress":
                key = data.get("key", 0)
                state = data.get("state", False)
                if self.key_callback:
                    self.key_callback(key, state)
                    
            elif data.get("event") == "deviceInfo":
                self.key_count = data.get("keyCount", 15)  # Standard: 15 Keys
                logger.info(f"📊 Tasten: {self.key_count}")
                
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten der Nachricht: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket Fehler"""
        logger.error(f"WebSocket Error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket geschlossen"""
        self.connected = False
        logger.info("VSDinside Stream Dock getrennt")
    
    def _send_message(self, message: dict):
        """Sendet Nachricht an Deck"""
        try:
            if self.ws and self.connected:
                self.ws.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Fehler beim Senden: {e}")
    
    def set_key_image(self, key: int, image_data: bytes):
        """Setzt Key-Bild"""
        try:
            import base64
            # Bild als Base64 encodieren
            img_b64 = base64.b64encode(image_data).decode('utf-8')
            
            self._send_message({
                "event": "setKeyImage",
                "key": key,
                "image": img_b64
            })
        except Exception as e:
            logger.error(f"Fehler beim Setzen von Key {key}: {e}")
    
    def set_brightness(self, percent: int):
        """Setzt Helligkeit"""
        self._send_message({
            "event": "setBrightness",
            "brightness": percent
        })
    
    def reset(self):
        """Resettet Deck"""
        self._send_message({"event": "reset"})
    
    def cleanup(self):
        """Cleanup"""
        try:
            self.running = False
            if self.ws:
                self.ws.close()
            if self.ws_thread:
                self.ws_thread.join(timeout=2)
            self.connected = False
            logger.info("✅ VSDinside Stream Dock getrennt")
        except Exception as e:
            logger.error(f"Fehler beim Cleanup: {e}")


class TouchPortalController(BaseDeckController):
    """
    Controller für Touch Portal App (Handy/Tablet als Stream Deck)
    Verwendet TouchPortal-API für Plugin-Integration
    """
    
    def __init__(self):
        super().__init__()
        self.tp_client = None
        self.running = False
        self.plugin_id = "schnuffs.promotionalerts.streamdeck"
        
    def initialize(self) -> bool:
        """Initialisiert Touch Portal Plugin"""
        try:
            import TouchPortalAPI as TP
            
            # Touch Portal Client erstellen
            self.tp_client = TP.Client(
                self.plugin_id,
                sleepPeriod=0.01,
                autoClose=True,
                checkPluginId=True,
                updateStatesOnBroadcast=True
            )
            
            # Event Handlers registrieren
            @self.tp_client.on(TP.TYPES.onConnect)
            def on_connect(data):
                self.connected = True
                logger.info(f"✅ Touch Portal verbunden: {data}")
                # Standard: 15 Buttons
                self.key_count = 15
                
            @self.tp_client.on(TP.TYPES.onAction)
            def on_action(data):
                """Wird aufgerufen wenn Button in Touch Portal gedrückt wird"""
                try:
                    # Touch Portal sendet action IDs wie "schnuffs.action.button0"
                    action_id = data.get('actionId', '')
                    
                    # Extrahiere Button-Nummer
                    if 'button' in action_id:
                        key = int(action_id.split('button')[-1])
                        if self.key_callback:
                            self.key_callback(key, True)
                            # Simuliere Release nach kurzer Zeit
                            import time
                            time.sleep(0.1)
                            self.key_callback(key, False)
                except Exception as e:
                    logger.error(f"Fehler beim Verarbeiten der Action: {e}")
            
            @self.tp_client.on(TP.TYPES.onShutdown)
            def on_shutdown(data):
                logger.info("Touch Portal wird geschlossen")
                self.connected = False
            
            # Verbindung in separatem Thread starten
            import threading
            self.running = True
            self.tp_thread = threading.Thread(target=self._run_client, daemon=True)
            self.tp_thread.start()
            
            # Warte kurz auf Verbindung
            import time
            time.sleep(1)
            
            if self.connected:
                logger.info("✅ Touch Portal Plugin bereit")
                return True
            else:
                logger.warning("Touch Portal App nicht verbunden")
                logger.info("Starte Touch Portal App und aktiviere das SchnuffsPromotionAlerts Plugin")
                return False
                
        except ImportError:
            logger.error("TouchPortal-API nicht installiert! pip install TouchPortal-API")
            return False
        except Exception as e:
            logger.error(f"Fehler bei Touch Portal Initialisierung: {e}")
            return False
    
    def _run_client(self):
        """Führt Touch Portal Client in Thread aus"""
        try:
            if self.tp_client:
                self.tp_client.connect()
        except Exception as e:
            logger.error(f"Touch Portal Client Fehler: {e}")
    
    def set_key_image(self, key: int, image_data: bytes):
        """
        Setzt Button-Bild in Touch Portal
        Touch Portal nutzt Base64-codierte Bilder
        """
        try:
            import base64
            
            if self.tp_client and self.connected:
                # State-ID für den Button
                state_id = f"{self.plugin_id}.state.button{key}.icon"
                
                # Bild als Base64 encodieren
                img_b64 = base64.b64encode(image_data).decode('utf-8')
                
                # State in Touch Portal updaten
                self.tp_client.stateUpdate(state_id, img_b64)
                
        except Exception as e:
            logger.error(f"Fehler beim Setzen von Button {key}: {e}")
    
    def set_brightness(self, percent: int):
        """Touch Portal unterstützt Helligkeit nicht direkt"""
        pass
    
    def reset(self):
        """Resettet alle Buttons"""
        try:
            if self.tp_client and self.connected:
                for key in range(self.key_count):
                    state_id = f"{self.plugin_id}.state.button{key}.icon"
                    self.tp_client.stateUpdate(state_id, "")
        except Exception as e:
            logger.error(f"Fehler beim Reset: {e}")
    
    def cleanup(self):
        """Cleanup"""
        try:
            self.running = False
            if self.tp_client:
                self.tp_client.disconnect()
            if hasattr(self, 'tp_thread'):
                self.tp_thread.join(timeout=2)
            self.connected = False
            logger.info("✅ Touch Portal getrennt")
        except Exception as e:
            logger.error(f"Fehler beim Cleanup: {e}")


class VirtualDeckController(BaseDeckController):
    """
    Virtuelles Deck - Software-Alternative ohne Hardware und ohne Touch Portal
    Wird direkt in PyQt6 GUI integriert
    """
    
    def __init__(self):
        super().__init__()
        self.key_states = {}
        
    def initialize(self) -> bool:
        """Initialisiert virtuelles Deck"""
        self.key_count = 15  # Standard: 15 Keys (3x5)
        self.connected = True
        
        for i in range(self.key_count):
            self.key_states[i] = {
                "image": None,
                "text": f"Key {i}",
                "icon": None
            }
        
        logger.info("✅ Virtuelles Stream Deck aktiviert (Software-Modus)")
        logger.info(f"📊 Tasten: {self.key_count}")
        return True
    
    def set_key_image(self, key: int, image_data: bytes):
        """Speichert Key-Bild (für GUI-Rendering)"""
        if 0 <= key < self.key_count:
            self.key_states[key]["image"] = image_data
    
    def set_brightness(self, percent: int):
        """Helligkeit (hat bei virtuellem Deck keine Funktion)"""
        pass
    
    def reset(self):
        """Resettet virtuelles Deck"""
        for key in self.key_states:
            self.key_states[key]["image"] = None
    
    def simulate_key_press(self, key: int, state: bool = True):
        """
        Simuliert Key-Press (wird von GUI aufgerufen)
        """
        if self.key_callback and 0 <= key < self.key_count:
            self.key_callback(key, state)
    
    def get_key_state(self, key: int) -> dict:
        """Gibt Key-State zurück (für GUI-Rendering)"""
        return self.key_states.get(key, {})
    
    def cleanup(self):
        """Cleanup"""
        self.connected = False
        logger.info("✅ Virtuelles Stream Deck deaktiviert")


class StreamDeckManager:
    """
    Hauptmanager - Erkennt automatisch verfügbare Decks und verwaltet sie
    """
    
    def __init__(self, use_virtual_fallback: bool = True):
        """
        Args:
            use_virtual_fallback: Falls True, wird virtuelles Deck als Fallback genutzt
        """
        self.controller: Optional[BaseDeckController] = None
        self.deck_type: Optional[str] = None
        self.use_virtual_fallback = use_virtual_fallback
        self.button_configs: Dict[int, dict] = {}
        
    def auto_detect_and_connect(self) -> bool:
        """
        Erkennt automatisch verfügbare Decks und verbindet sich
        Priorität: 1. Elgato, 2. VSDinside, 3. Touch Portal, 4. Virtual (Fallback)
        """
        logger.info("🔍 Suche nach Stream Deck Geräten...")
        
        # Versuch 1: Elgato Stream Deck
        logger.info("Versuche Elgato Stream Deck...")
        elgato = ElgatoStreamDeckController()
        if elgato.initialize():
            self.controller = elgato
            self.deck_type = "elgato"
            logger.info("✅ Elgato Stream Deck wird verwendet")
            return True
        
        # Versuch 2: VSDinside Stream Dock
        logger.info("Versuche VSDinside Stream Dock...")
        vsdinside = VSDinsideStreamDockController()
        if vsdinside.initialize():
            self.controller = vsdinside
            self.deck_type = "vsdinside"
            logger.info("✅ VSDinside Stream Dock wird verwendet")
            return True
        
        # Versuch 3: Touch Portal (Handy/Tablet App)
        logger.info("Versuche Touch Portal...")
        touchportal = TouchPortalController()
        if touchportal.initialize():
            self.controller = touchportal
            self.deck_type = "touchportal"
            logger.info("✅ Touch Portal wird verwendet")
            return True
        
        # Versuch 4: Virtuelles Deck (Fallback)
        if self.use_virtual_fallback:
            logger.info("Verwende virtuelles Stream Deck (Software-Modus)...")
            virtual = VirtualDeckController()
            if virtual.initialize():
                self.controller = virtual
                self.deck_type = "virtual"
                logger.info("✅ Virtuelles Stream Deck wird verwendet")
                return True
        
        logger.error("❌ Kein Stream Deck gefunden!")
        return False
    
    def connect_specific(self, deck_type: str) -> bool:
        """
        Verbindet zu spezifischem Deck-Typ
        
        Args:
            deck_type: "elgato", "vsdinside", "touchportal" oder "virtual"
        """
        if deck_type == "elgato":
            self.controller = ElgatoStreamDeckController()
        elif deck_type == "vsdinside":
            self.controller = VSDinsideStreamDockController()
        elif deck_type == "touchportal":
            self.controller = TouchPortalController()
        elif deck_type == "virtual":
            self.controller = VirtualDeckController()
        else:
            logger.error(f"Unbekannter Deck-Typ: {deck_type}")
            return False
        
        if self.controller.initialize():
            self.deck_type = deck_type
            return True
        return False
    
    def create_button_image(self, text: str, icon_path: Optional[str] = None, 
                           bg_color: str = "black", text_color: str = "white") -> bytes:
        """
        Erstellt ein Button-Bild (72x72px für Standard Stream Deck)
        
        Args:
            text: Text auf dem Button
            icon_path: Pfad zum Icon (optional)
            bg_color: Hintergrundfarbe
            text_color: Textfarbe
        """
        # Bild erstellen
        image = Image.new("RGB", (72, 72), bg_color)
        draw = ImageDraw.Draw(image)
        
        # Icon laden (falls vorhanden)
        if icon_path and Path(icon_path).exists():
            try:
                icon = Image.open(icon_path)
                # Icon auf 50x50 skalieren
                icon.thumbnail((50, 50), Image.Resampling.LANCZOS)
                # Icon zentriert oben platzieren
                x = (72 - icon.width) // 2
                y = 5
                image.paste(icon, (x, y), icon if icon.mode == 'RGBA' else None)
            except Exception as e:
                logger.error(f"Fehler beim Laden des Icons: {e}")
        
        # Text hinzufügen
        try:
            # Versuche schönere Font zu laden
            try:
                font = ImageFont.truetype("arial.ttf", 10)
            except:
                font = ImageFont.load_default()
            
            # Text umbrechen wenn zu lang
            words = text.split('\n')
            y_text = 55 if icon_path else 25
            
            for word in words:
                bbox = draw.textbbox((0, 0), word, font=font)
                text_width = bbox[2] - bbox[0]
                x_text = (72 - text_width) // 2
                draw.text((x_text, y_text), word, font=font, fill=text_color)
                y_text += 12
                
        except Exception as e:
            logger.error(f"Fehler beim Rendern des Textes: {e}")
        
        # Für Elgato: Native Format konvertieren
        if self.deck_type == "elgato" and self.controller:
            try:
                from StreamDeck.ImageHelpers import PILHelper
                return PILHelper.to_native_format(self.controller.deck, image)
            except:
                pass
        
        # Für andere: Als PNG bytes
        from io import BytesIO
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def set_button(self, key: int, text: str, icon_path: Optional[str] = None,
                   bg_color: str = "black", text_color: str = "white"):
        """
        Setzt einen Button mit Text und optionalem Icon
        """
        if not self.controller or not self.controller.connected:
            logger.warning("Kein Deck verbunden!")
            return
        
        # Button-Konfiguration speichern
        self.button_configs[key] = {
            "text": text,
            "icon": icon_path,
            "bg_color": bg_color,
            "text_color": text_color
        }
        
        # Bild erstellen und setzen
        image_data = self.create_button_image(text, icon_path, bg_color, text_color)
        self.controller.set_key_image(key, image_data)
    
    def register_button_callback(self, callback: Callable[[int, bool], None]):
        """
        Registriert Callback für Button-Presses
        
        Args:
            callback: Funktion die aufgerufen wird (key: int, pressed: bool)
        """
        if self.controller:
            self.controller.register_key_callback(callback)
    
    def set_brightness(self, percent: int):
        """Setzt Helligkeit (0-100)"""
        if self.controller:
            self.controller.set_brightness(max(0, min(100, percent)))
    
    def reset(self):
        """Resettet das Deck"""
        if self.controller:
            self.controller.reset()
            self.button_configs.clear()
    
    def cleanup(self):
        """Räumt auf und trennt Verbindung"""
        if self.controller:
            self.controller.cleanup()
            self.controller = None
            self.deck_type = None
    
    def is_connected(self) -> bool:
        """Prüft ob ein Deck verbunden ist"""
        return self.controller is not None and self.controller.connected
    
    def get_key_count(self) -> int:
        """Gibt Anzahl der Tasten zurück"""
        return self.controller.key_count if self.controller else 0
    
    def get_deck_type(self) -> Optional[str]:
        """Gibt Deck-Typ zurück"""
        return self.deck_type


# ============================================================================
# Beispiel-Nutzung für SchnuffsPromotionAlerts
# ============================================================================

class SchnuffsStreamDeckIntegration:
    """
    Integration für SchnuffsPromotionAlerts
    Zeigt wie der Manager verwendet wird
    """
    
    def __init__(self, twitch_watcher=None):
        self.manager = StreamDeckManager(use_virtual_fallback=True)
        self.twitch_watcher = twitch_watcher
        self.monitoring_active = False
        
    def initialize(self) -> bool:
        """Initialisiert Stream Deck"""
        if not self.manager.auto_detect_and_connect():
            logger.error("Stream Deck konnte nicht initialisiert werden")
            return False
        
        # Callbacks registrieren
        self.manager.register_button_callback(self.on_button_press)
        
        # Buttons einrichten
        self.setup_buttons()
        
        return True
    
    def setup_buttons(self):
        """Richtet alle Buttons ein"""
        logger.info("Richte Buttons ein...")
        
        # Button 0: Start/Stop Monitoring
        self.manager.set_button(
            0, 
            "Start\nMonitoring",
            icon_path="assets/logo.png",
            bg_color="darkgreen"
        )
        
        # Button 1: Dashboard
        self.manager.set_button(
            1,
            "Dashboard",
            bg_color="darkblue"
        )
        
        # Button 2: Settings
        self.manager.set_button(
            2,
            "Settings",
            bg_color="gray"
        )
        
        # Button 3: Discord Toggle
        self.manager.set_button(
            3,
            "Discord\nON",
            bg_color="purple"
        )
        
        # Button 4: Webcam Test
        self.manager.set_button(
            4,
            "Webcam\nTest",
            bg_color="orange"
        )
        
        # Button 5-14: Weitere Funktionen...
        for i in range(5, min(15, self.manager.get_key_count())):
            self.manager.set_button(i, f"Funktion\n{i}", bg_color="black")
    
    def on_button_press(self, key: int, pressed: bool):
        """
        Wird aufgerufen wenn Button gedrückt wird
        """
        if not pressed:  # Nur bei Press, nicht bei Release
            return
        
        logger.info(f"🎮 Button {key} gedrückt!")
        
        # Button-Actions
        if key == 0:
            self.toggle_monitoring()
        elif key == 1:
            self.open_dashboard()
        elif key == 2:
            self.open_settings()
        elif key == 3:
            self.toggle_discord()
        elif key == 4:
            self.start_webcam_test()
    
    def toggle_monitoring(self):
        """Start/Stop Monitoring"""
        self.monitoring_active = not self.monitoring_active
        
        if self.monitoring_active:
            logger.info("▶️ Monitoring gestartet!")
            self.manager.set_button(0, "Stop\nMonitoring", bg_color="darkred")
            # Hier: self.twitch_watcher.start()
        else:
            logger.info("⏹️ Monitoring gestoppt!")
            self.manager.set_button(0, "Start\nMonitoring", bg_color="darkgreen")
            # Hier: self.twitch_watcher.stop()
    
    def open_dashboard(self):
        """Öffnet Dashboard"""
        logger.info("📊 Dashboard öffnen")
        # Hier: Signal an GUI senden um zur Dashboard-Page zu wechseln
    
    def open_settings(self):
        """Öffnet Settings"""
        logger.info("⚙️ Settings öffnen")
        # Hier: Signal an GUI senden
    
    def toggle_discord(self):
        """Discord Notifications an/aus"""
        logger.info("💬 Discord Toggle")
        # Hier: Discord Notifications umschalten
    
    def start_webcam_test(self):
        """Startet Webcam Test"""
        logger.info("📹 Webcam Test starten")
        # Hier: Webcam Test starten
    
    def cleanup(self):
        """Cleanup"""
        self.manager.cleanup()


# ============================================================================
# Demo / Test
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🎮 Universal StreamDeck Manager - Demo")
    print("=" * 70)
    print()
    
    # Integration erstellen
    integration = SchnuffsStreamDeckIntegration()
    
    if integration.initialize():
        print(f"\n✅ Stream Deck bereit! ({integration.manager.get_deck_type()})")
        print(f"📊 Tasten verfügbar: {integration.manager.get_key_count()}")
        print("\n🎮 Drücke Buttons auf dem Stream Deck!")
        print("   Oder drücke Ctrl+C zum Beenden\n")
        
        try:
            # Programm am Laufen halten
            import time
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n⚠️ Beende...")
        finally:
            integration.cleanup()
            print("✅ Beendet!")
    else:
        print("\n❌ Konnte kein Stream Deck initialisieren!")
        print("Stelle sicher dass:")
        print("  - Ein Deck angeschlossen ist")
        print("  - Die nötigen Libraries installiert sind:")
        print("    pip install streamdeck pillow websocket-client")