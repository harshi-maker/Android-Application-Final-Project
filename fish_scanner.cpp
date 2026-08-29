#include <opencv2/opencv.hpp>
#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <sstream>

// ==========================================
// 1. CONFIGURATION & ALLOMETRIC CONSTANTS
// ==========================================
// Pixels per centimeter (calibrate based on your camera distance)
const double DEFAULT_PPM = 22.5; 

// Allometric Weight constants: Weight (g) = A * (Length_cm ^ B)
const double A_PARAM = 0.015;
const double B_PARAM = 3.02;

// Minimum contour area to reject background noise/specks
const double MIN_FISH_AREA = 4000.0;

int main() {
    // 0 = Default webcam / integrated camera
    cv::VideoCapture cap(0);

    // Set buffer size to 1 to minimize video latency
    cap.set(cv::CAP_PROP_BUFFERSIZE, 1);

    if (!cap.isOpened()) {
        std::cerr << "Error: Unable to access the camera." << std::endl;
        return -1;
    }

    cv::Mat frame, gray, blurred, thresh;
    cv::Mat morphKernel = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(7, 7));

    const std::string windowName = "Offline C++ Fish Scanner";
    cv::namedWindow(windowName, cv::WINDOW_AUTOSIZE);

    std::cout << "Starting Fish Scanner. Press 'q' or 'ESC' to exit." << std::endl;

    while (true) {
        cap >> frame;
        if (frame.empty()) break;

        // 1. Convert to grayscale and blur to remove noise/specular highlights
        cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);
        cv::GaussianBlur(gray, blurred, cv::Size(5, 5), 0);

        // 2. Otsu thresholding to segment fish from tray surface
        cv::threshold(blurred, thresh, 0, 255, cv::THRESH_BINARY_INV + cv::THRESH_OTSU);

        // 3. Clean up threshold mask (fill holes and remove stray surface specks)
        cv::morphologyEx(thresh, thresh, cv::MORPH_CLOSE, morphKernel, cv::Point(-1, -1), 2);
        cv::morphologyEx(thresh, thresh, cv::MORPH_OPEN, morphKernel, cv::Point(-1, -1), 1);

        // 4. Find all external contours
        std::vector<std::vector<cv::Point>> contours;
        cv::findContours(thresh, contours, cv::RETR_EXTERNAL, cv::CHAIN_APPROX_SIMPLE);

        int largestIdx = -1;
        double maxArea = MIN_FISH_AREA;

        for (size_t i = 0; i < contours.size(); ++i) {
            double area = cv::contourArea(contours[i]);
            if (area > maxArea) {
                maxArea = area;
                largestIdx = static_cast<int>(i);
            }
        }

        cv::Mat displayFrame;

        if (largestIdx != -1) {
            const std::vector<cv::Point>& fishContour = contours[largestIdx];

            // 5. INTERNAL CALCULATION (No dot markers rendered)
            cv::RotatedRect minRect = cv::minAreaRect(fishContour);
            double w_px = std::min(minRect.size.width, minRect.size.height);
            double l_px = std::max(minRect.size.width, minRect.size.height);

            double length_cm = l_px / DEFAULT_PPM;
            double width_cm  = w_px / DEFAULT_PPM;

            // Accurate Allometric Weight: W = a * (L^b)
            double weight_g = A_PARAM * std::pow(length_cm, B_PARAM);

            // 6. ISOLATE ONLY THE FISH (Set background to black)
            cv::Mat fishMask = cv::Mat::zeros(gray.size(), CV_8UC1);
            cv::drawContours(fishMask, contours, largestIdx, cv::Scalar(255), -1);

            displayFrame = cv::Mat::zeros(frame.size(), frame.type());
            frame.copyTo(displayFrame, fishMask);

            // Draw smooth green perimeter outline
            cv::drawContours(displayFrame, contours, largestIdx, cv::Scalar(0, 255, 0), 2);

            // 7. Render Clean HUD Text
            std::stringstream ssL, ssW, ssWt;
            ssL << std::fixed << std::setprecision(2) << "Length: " << length_cm << " cm";
            ssW << std::fixed << std::setprecision(2) << "Width:  " << width_cm << " cm";
            ssWt << std::fixed << std::setprecision(1) << "Weight: " << weight_g << " g";

            cv::putText(displayFrame, ssL.str(), cv::Point(25, 45), 
                        cv::FONT_HERSHEY_SIMPLEX, 0.75, cv::Scalar(0, 255, 0), 2);
            cv::putText(displayFrame, ssW.str(), cv::Point(25, 80), 
                        cv::FONT_HERSHEY_SIMPLEX, 0.75, cv::Scalar(255, 255, 0), 2);
            cv::putText(displayFrame, ssWt.str(), cv::Point(25, 115), 
                        cv::FONT_HERSHEY_SIMPLEX, 0.75, cv::Scalar(0, 200, 255), 2);
        } else {
            // If no fish is on the tray, show normal camera feed
            displayFrame = frame;
        }

        cv::imshow(windowName, displayFrame);

        // Press 'q' or 'ESC' (27) to exit
        char key = static_cast<char>(cv::waitKey(1));
        if (key == 'q' || key == 27) {
            break;
        }
    }

    cap.release();
    cv::destroyAllWindows();
    return 0;
}
