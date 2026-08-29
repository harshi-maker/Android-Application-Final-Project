import cv2
import numpy as np

# ==========================================
# 1. CALIBRATION & SPECIES CONFIGURATION
# ==========================================
# ArUco Marker real-world width in cm (e.g., a printed 5.0 cm marker on the tray)
MARKER_REAL_WIDTH_CM = 5.0

# Allometric Weight Parameters: W = a * (L^b)
# Default values for generic fish (e.g., Tilapia, Trout, Carp)
A_PARAM = 0.015
B_PARAM = 3.02

# Dictionary for ArUco detector
try:
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
except AttributeError:
    # Legacy OpenCV compatibility
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
    aruco_params = cv2.aruco.DetectorParameters_create()
    detector = None

def get_pixels_per_cm(frame):
    """Detects ArUco marker on the scanning surface to calibrate scale in real time."""
    if detector is not None:
        corners, ids, _ = detector.detectMarkers(frame)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(frame, aruco_dict, parameters=aruco_params)

    if ids is not None and len(corners) > 0:
        c = corners[0][0]
        # Pixel width of top edge of the marker
        marker_px_w = np.linalg.norm(c[0] - c[1])
        ppm = marker_px_w / MARKER_REAL_WIDTH_CM
        # Draw marker outline
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
        return ppm
    return None

def process_fish(frame, ppm):
    """Isolates the fish, places dot markers on key anatomical points, and calculates metrics."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)

    # Adaptive / Otsu Thresholding to separate fish from background
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Clean noise (remove small dots on surface)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return frame

    # Filter out the ArUco marker by area/aspect and select the largest organic contour (the fish)
    valid_contours = [c for c in contours if cv2.contourArea(c) > 3000]
    if not valid_contours:
        return frame

    fish_contour = max(valid_contours, key=cv2.contourArea)

    # 1. Fit an ellipse / minimum area rectangle to align along the fish spine
    rect = cv2.minAreaRect(fish_contour)
    (cx, cy), (w_px, h_px), angle = rect

    # 2. Extract extreme anatomical landmark points
    # Leftmost, Rightmost, Topmost, Bottommost relative to contour orientation
    ext_left = tuple(fish_contour[fish_contour[:, :, 0].argmin()][0])
    ext_right = tuple(fish_contour[fish_contour[:, :, 0].argmax()][0])
    ext_top = tuple(fish_contour[fish_contour[:, :, 1].argmin()][0])
    ext_bot = tuple(fish_contour[fish_contour[:, :, 1].argmax()][0])

    # 3. Calculate Dimensions
    length_px = max(w_px, h_px)
    width_px = min(w_px, h_px)

    length_cm = length_px / ppm
    width_cm = width_px / ppm

    # 4. Accurate Allometric Weight: W = a * (L^b)
    weight_g = A_PARAM * (length_cm ** B_PARAM)

    # -------------------------------------------------------------
    # 5. DRAWING & DOT MARKERS ONLY ON THE FISH
    # -------------------------------------------------------------
    # Draw contour outline of the fish
    cv2.drawContours(frame, [fish_contour], -1, (0, 255, 0), 2)

    # Dot Markers on Key Anatomical Extremes
    # Green = Snout / Head, Red = Tail / Caudal, Cyan = Dorsal / Ventral thickness
    cv2.circle(frame, ext_left, 6, (0, 255, 0), -1)   # Snout/Tail dot
    cv2.circle(frame, ext_right, 6, (0, 0, 255), -1)  # Tail/Snout dot
    cv2.circle(frame, ext_top, 6, (255, 255, 0), -1)   # Top dorsal dot
    cv2.circle(frame, ext_bot, 6, (255, 255, 0), -1)   # Bottom ventral dot

    # Center of mass dot
    cv2.circle(frame, (int(cx), int(cy)), 5, (0, 255, 255), -1)

    # Connect length and width measurement axes
    cv2.line(frame, ext_left, ext_right, (0, 255, 0), 2)
    cv2.line(frame, ext_top, ext_bot, (255, 255, 0), 2)

    # Display Metrics Overlay
    cv2.putText(frame, f"Length: {length_cm:.2f} cm", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"Width:  {width_cm:.2f} cm", (20, 75), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    cv2.putText(frame, f"Weight: {weight_g:.1f} g", (20, 110), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2)

    return frame

# ==========================================
# 2. MAIN CAMERA LOOP
# ==========================================
def main():
    cap = cv2.VideoCapture(0)  # Change index if using external USB camera
    
    # Fallback default calibration (approx 20 px/cm) if marker is temporarily not detected
    cached_ppm = 20.0  

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Check for ArUco calibration marker on the surface
        detected_ppm = get_pixels_per_cm(frame)
        if detected_ppm is not None:
            cached_ppm = detected_ppm
            cv2.putText(frame, "Scale Calibrated (Marker OK)", (20, frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(frame, "Using Last Known Scale", (20, frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

        # Process fish segmentation, dot markers, and metrics
        frame = process_fish(frame, cached_ppm)

        cv2.imshow("Fish Measurement Scanner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
