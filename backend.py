import cv2
import torch
import face_recognition
import pickle
import winsound
from gtts import gTTS
import pygame
from io import BytesIO

# Load YOLOv5 model
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
model.eval()

# Load COCO names file
with open("F:/TheObserver/coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]

# Load known faces and encodings
try:
    with open("F:/TheObserver/cache/known_face_encoding.pkl", "rb") as f:
        known_face_encoding = pickle.load(f)
except FileNotFoundError:
    known_face_encoding = []

try:
    with open("F:/TheObserver/cache/known_faces_names.pkl", "rb") as f:
        known_faces_names = pickle.load(f)
except FileNotFoundError:
    known_faces_names = []

def generate_alert_speech(object_label):
    """
    Generate and play an alert speech when a specified object is detected.
    
    Args:
        object_label (str): The label of the detected object.
    """
    text = f"Alert! {object_label} detected!"
    tts = gTTS(text=text, lang="en", slow=False)
    mp3_fp = BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    pygame.init()
    pygame.mixer.music.load(mp3_fp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

def generate_speech():
    """
    Generate and play an alert speech when an unknown person is detected.
    """
    text = "Unknown person detected!"
    tts = gTTS(text=text, lang="en", slow=False)
    mp3_fp = BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    pygame.init()
    pygame.mixer.music.load(mp3_fp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

def add_user(name):
    """
    Add a new user to the known faces list.
    
    Args:
        name (str): The name of the user to be added.
    """
    user_image = face_recognition.load_image_file("F:/TheObserver/photos/"+name.replace(" ", "_")+".jpg")
    user_encoding = face_recognition.face_encodings(user_image)[0]
    known_face_encoding.append(user_encoding)
    known_faces_names.append(name)
    with open("F:/TheObserver/cache/known_face_encoding.pkl", "wb") as f:
        pickle.dump(known_face_encoding, f)
    with open("F:/TheObserver/cache/known_faces_names.pkl", "wb") as f:
        pickle.dump(known_faces_names, f)

def detect_and_recognize(frame):
    """
    Detect and recognize humans and specified objects within a given frame.
    
    Args:
        frame (ndarray): The input video frame.
    
    Returns:
        frame (ndarray): The processed video frame with annotations.
    """
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB

    alert_detected = False
    detected_object_label = ""

    # Perform object detection
    results = model(frame_rgb)

    # Process the detections
    for det in results.pred[0]:
        label = classes[int(det[5])]
        bbox = det[:4].int().cpu().numpy()
        x, y, x_max, y_max = bbox

        # If the detected object is a person (class index 0 is usually "person")
        if int(det[5]) == 0:
            x, y, x_max, y_max = int(x), int(y), int(x_max), int(y_max)  # Convert to integer as OpenCV expects integers
            cv2.rectangle(frame, (x, y), (x_max, y_max), (0, 255, 0), 2)  # Draw bounding box and label

        # If the detected object is one of the specified classes
        if label in ["bag", "cell phone", "knife", "gun", "laptop", "mouse", "remote", "keyboard"]:
            x, y, x_max, y_max = int(x), int(y), int(x_max), int(y_max)  # Convert to integer as OpenCV expects integers
            cv2.rectangle(frame, (x, y), (x_max, y_max), (0, 0, 255), 2)  # Draw bounding box and label
            cv2.putText(frame, f"{label}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            alert_detected = True
            detected_object_label = label  # Set the alert flag to True and store the detected object label

    # Generate an alert if any specified object is detected
    if alert_detected:
        generate_alert_speech(detected_object_label)
        
    # Recognize faces
    face_locations = face_recognition.face_locations(frame_rgb)
    face_encodings = face_recognition.face_encodings(frame_rgb, face_locations)
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_face_encoding, face_encoding, tolerance=0.5)  # Adjust tolerance as needed
        name = "Unknown"
        if True in matches:
            first_match_index = matches.index(True)
            name = known_faces_names[first_match_index]
        else:
            winsound.Beep(1000, 500)  # Beep when an unknown person is detected (Adjust the frequency and duration of the beep as needed)
            generate_speech()

        top -= 10  # Adjust position for displaying the name
        cv2.putText(frame, f"{name}", (left, top), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    return frame

def detect_and_recognize_people():
    """
    Capture video from the camera, perform human detection and facial recognition, 
    and display the processed video frames.
    """
    video = cv2.VideoCapture(0)  # Change the camera index to the appropriate one for the iriun 4K webcam

    if not video.isOpened():
        print("Error: Could not open camera. Please check the camera index.")
        return

    while True:
        ret, frame = video.read()

        if not ret:  # Check if a frame was successfully read
            print("Error: Could not read frame from the camera.")
            break

        frame_processed = detect_and_recognize(frame)
        frame_display = cv2.resize(frame_processed, (frame.shape[1], frame.shape[0]))  # Resize the processed frame back to the original size for display

        cv2.imshow('Human Detection and Facial Recognition', frame_display)

        key = cv2.waitKey(1)  # Check for key events

        if key == ord('q') or key == 27:  # Close window if the user presses the 'q' key or the close button (X)
            break

        if cv2.getWindowProperty('Human Detection and Facial Recognition', cv2.WND_PROP_VISIBLE) < 1:
            break

    video.release()
    cv2.destroyAllWindows()
