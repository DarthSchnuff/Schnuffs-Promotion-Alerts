import cv2
import numpy as np
import sys

def apply_effects(frame, effect_type):
    """
    Wendet verschiedene Effekte auf das Kamera-Bild an.
    
    HINWEIS: Dies testet nur die HARDWARE-Performance (Kamera-FPS, Auflösung).
    Die Software-Effekte dienen nur zur visuellen Demonstration.
    """
    if effect_type == 'none':
        return frame
    
    elif effect_type == 'grayscale':
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    elif effect_type == 'blur':
        return cv2.GaussianBlur(frame, (15, 15), 0)
    
    elif effect_type == 'edge':
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.Canny(gray, 50, 150)
    
    elif effect_type == 'sepia':
        kernel = np.array([[0.272, 0.534, 0.131],
                          [0.349, 0.686, 0.168],
                          [0.393, 0.769, 0.189]])
        return cv2.transform(frame, kernel)
    
    elif effect_type == 'invert':
        return cv2.bitwise_not(frame)
    
    elif effect_type == 'brightness':
        return cv2.convertScaleAbs(frame, alpha=1.5, beta=30)
    
    return frame

def test_camera_with_effects():
    """
    HARDWARE-TEST für die Webcam mit visuellen Effekten.
    
    WICHTIG: Dieser Test prüft die HARDWARE (Kamera-FPS, Stabilität, Auflösung).
    Die Effekte sind nur zur Demonstration und testen NICHT die Software-Integration!
    
    Steuerung:
    - 'q': Beenden
    - '1': Kein Effekt
    - '2': Graustufen
    - '3': Weichzeichner
    - '4': Kantenerkennung
    - '5': Sepia
    - '6': Invertiert
    - '7': Helligkeit erhöht
    """
    
    # Kamera initialisieren
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ FEHLER: Kamera konnte nicht geöffnet werden!")
        print("Überprüfe, ob die Kamera angeschlossen und verfügbar ist.")
        return
    
    # Kamera-Eigenschaften setzen
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("=" * 70)
    print("🎥 KAMERA HARDWARE-TEST für SchnuffsPromotionAlerts")
    print("=" * 70)
    print("⚠️  HINWEIS: Dies ist ein HARDWARE-Test!")
    print("   - Testet: Kamera-FPS, Auflösung, Stabilität")
    print("   - Testet NICHT: Software-Integration in dein Programm")
    print("=" * 70)
    print(f"📹 Auflösung: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print(f"⚡ Ziel-FPS: {int(cap.get(cv2.CAP_PROP_FPS))}")
    print("=" * 70)
    print("\n🎮 Steuerung:")
    print("  Q - Beenden")
    print("  1 - Kein Effekt (Standard)")
    print("  2 - Graustufen")
    print("  3 - Weichzeichner")
    print("  4 - Kantenerkennung")
    print("  5 - Sepia")
    print("  6 - Invertiert")
    print("  7 - Helligkeit erhöht")
    print("=" * 70)
    
    current_effect = 'none'
    effect_names = {
        'none': 'Kein Effekt',
        'grayscale': 'Graustufen',
        'blur': 'Weichzeichner',
        'edge': 'Kantenerkennung',
        'sepia': 'Sepia',
        'invert': 'Invertiert',
        'brightness': 'Helligkeit erhöht'
    }
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("❌ Fehler beim Lesen des Frames!")
                break
            
            frame_count += 1
            
            # Effekt anwenden
            processed_frame = apply_effects(frame, current_effect)
            
            # Wenn Graustufen oder Kantenerkennung, zurück zu BGR konvertieren für Textanzeige
            if len(processed_frame.shape) == 2:
                display_frame = cv2.cvtColor(processed_frame, cv2.COLOR_GRAY2BGR)
            else:
                display_frame = processed_frame.copy()
            
            # Informationen auf dem Bild anzeigen
            cv2.putText(display_frame, f"Hardware-Test - Frame: {frame_count}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Effekt: {effect_names[current_effect]}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, "Druecke Q zum Beenden", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            
            # Frame anzeigen
            cv2.imshow('SchnuffsPromotionAlerts - Kamera Hardware-Test', display_frame)
            
            # Tastendruck verarbeiten
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("\n✅ Beende Hardware-Test...")
                break
            elif key == ord('1'):
                current_effect = 'none'
                print(f"🎨 Effekt: {effect_names[current_effect]}")
            elif key == ord('2'):
                current_effect = 'grayscale'
                print(f"🎨 Effekt: {effect_names[current_effect]}")
            elif key == ord('3'):
                current_effect = 'blur'
                print(f"🎨 Effekt: {effect_names[current_effect]}")
            elif key == ord('4'):
                current_effect = 'edge'
                print(f"🎨 Effekt: {effect_names[current_effect]}")
            elif key == ord('5'):
                current_effect = 'sepia'
                print(f"🎨 Effekt: {effect_names[current_effect]}")
            elif key == ord('6'):
                current_effect = 'invert'
                print(f"🎨 Effekt: {effect_names[current_effect]}")
            elif key == ord('7'):
                current_effect = 'brightness'
                print(f"🎨 Effekt: {effect_names[current_effect]}")
                
    except KeyboardInterrupt:
        print("\n⚠️  Programm durch Benutzer unterbrochen.")
    
    finally:
        # WICHTIG: Kamera freigeben und Fenster schließen
        print("\n🔧 Gebe Kamera-Hardware frei...")
        cap.release()
        cv2.destroyAllWindows()
        
        # Extra Wartezeit für sauberes Cleanup
        cv2.waitKey(1)
        
        print("=" * 70)
        print(f"✅ Hardware-Test abgeschlossen!")
        print(f"📊 Frames verarbeitet: {frame_count}")
        print("✅ Kamera erfolgreich freigegeben - Keine FPS-Probleme!")
        print("=" * 70)

if __name__ == "__main__":
    test_camera_with_effects()