#include <WiFi.h>
#include <FirebaseESP32.h>
#include <time.h>  // For NTP time

// 🔹 WiFi Credentials
#define WIFI_SSID "BottleFi"
#define WIFI_PASSWORD "BottleFi123"

// 🔹 Firebase Credentials
#define FIREBASE_HOST "https://watersensorcoms-default-rtdb.asia-southeast1.firebasedatabase.app/"
#define FIREBASE_AUTH "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"

// 🔹 HC-SR04 Pins
#define TRIG_PIN 12
#define ECHO_PIN 14

// 🔹 Firebase Setup
FirebaseData firebaseData;
FirebaseAuth auth;
FirebaseConfig config;

// 🔹 NTP Time Configuration (GMT+8 for PH Time)
const long gmtOffset_sec = 8 * 3600;
const int daylightOffset_sec = 0;

// 🔹 Timing
unsigned long lastDistanceCheck = 0;
unsigned long lastFirebaseUpdate = 0;
const unsigned long distanceInterval = 2000;   // 2 seconds
const unsigned long firebaseInterval = 5000;   // 5 seconds

float distanceCM = 0;

void connectWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int retryCount = 0;
  while (WiFi.status() != WL_CONNECTED && retryCount < 15) {
    Serial.print(".");
    delay(1000);
    retryCount++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected!");
  } else {
    Serial.println("\n❌ Failed to connect to WiFi! Restarting...");
    ESP.restart();
  }
}

void syncTime() {
  Serial.println("⏳ Syncing time with NTP...");
  configTime(gmtOffset_sec, daylightOffset_sec, "pool.ntp.org", "time.nist.gov");

  struct tm timeinfo;
  int retry = 0;
  while (!getLocalTime(&timeinfo) && retry < 10) {
    Serial.print(".");
    delay(1000);
    retry++;
  }

  if (getLocalTime(&timeinfo)) {
    Serial.println("\n✅ Time synchronized!");
  } else {
    Serial.println("\n❌ Failed to obtain time! Restarting...");
    ESP.restart();
  }
}

float measureDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30 ms timeout
  float distance = duration * 0.034 / 2;

  if (duration == 0) {
    Serial.println("⚠️ No echo received (timeout).");
    return -1;
  }

  return distance;
}

void setup() {
  Serial.begin(115200);

  // Pin Setup
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Connect WiFi
  connectWiFi();

  // Sync time
  syncTime();

  // Init Firebase
  config.host = FIREBASE_HOST;
  config.signer.tokens.legacy_token = FIREBASE_AUTH;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
}

void loop() {
  unsigned long now = millis();

  // 🔹 Measure Distance
  if (now - lastDistanceCheck >= distanceInterval) {
    lastDistanceCheck = now;
    float newDistance = measureDistanceCM();

    if (newDistance >= 0) {
      distanceCM = newDistance;
      Serial.print("📏 Distance: ");
      Serial.print(distanceCM);
      Serial.println(" cm");
    }
  }

  // 🔹 Send to Firebase
  if (now - lastFirebaseUpdate >= firebaseInterval) {
    lastFirebaseUpdate = now;

    struct tm timeinfo;
    if (getLocalTime(&timeinfo)) {
      char timeString[30];
      strftime(timeString, sizeof(timeString), "%Y-%m-%d %H:%M:%S", &timeinfo);
      Serial.print("🕒 Timestamp: ");
      Serial.println(timeString);

      if (Firebase.setFloat(firebaseData, "/HC_SR04/Distance", distanceCM)) {
        Serial.println("✅ Distance uploaded to Firebase");
      } else {
        Serial.println("❌ Distance upload failed: " + firebaseData.errorReason());
      }

      if (Firebase.setString(firebaseData, "/HC_SR04/Timestamp", timeString)) {
        Serial.println("✅ Timestamp uploaded to Firebase");
      } else {
        Serial.println("❌ Timestamp upload failed: " + firebaseData.errorReason());
      }
    } else {
      Serial.println("⚠️ Cannot get time for Firebase update");
    }
  }
}
