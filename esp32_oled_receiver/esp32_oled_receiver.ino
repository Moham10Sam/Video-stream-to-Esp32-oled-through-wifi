/*
  esp32_oled_receiver_wifi.ino
  Same job as the Bluetooth version, but over WiFi (TCP) instead of BT SPP.
  ESP32-CAM joins your WiFi network and runs a TCP server; playback.py
  connects to it as a client and streams frames.

  Protocol identical to the BT version: 2 sync bytes [0xAA, 0x55] followed
  by exactly 1024 payload bytes (SSD1306 page-format buffer).

  Board: AI-Thinker ESP32-CAM.
    SDA -> GPIO15, SCL -> GPIO14 (see wiring notes from earlier)
  Libraries needed: Adafruit GFX, Adafruit SSD1306 (WiFi.h is built-in).
*/

#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ---- fill these in ----
const char* WIFI_SSID = "Galaxy F12 8524";
const char* WIFI_PASS = "hsbdhs72";
const uint16_t TCP_PORT = 3333;
// ------------------------

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define FRAME_BYTES 1024

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
WiFiServer server(TCP_PORT);
WiFiClient client;

uint8_t frameBuf[FRAME_BYTES];

void connectWiFi() {
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("Connected. IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nConnect attempt timed out, will retry in loop().");
  }
}

void setup() {
  Serial.begin(115200);

  Wire.begin(15, 14);  // SDA=GPIO15, SCL=GPIO14
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 init failed");
    while (true) delay(1000);
  }
  display.clearDisplay();
  display.display();

  WiFi.setSleep(false);  // disable WiFi power-save; it's a common cause of random drops on ESP32-CAM
  connectWiFi();

  server.begin();
  Serial.println("TCP server started, waiting for connection...");
}

bool readExact(WiFiClient &c, uint8_t *buf, size_t n, uint32_t timeoutMs = 3000) {
  size_t got = 0;
  uint32_t start = millis();
  while (got < n) {
    if (c.available()) {
      int r = c.read(buf + got, n - got);
      if (r > 0) got += r;
    }
    if (millis() - start > timeoutMs) return false;
    if (!c.connected()) return false;
  }
  return true;
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi dropped, reconnecting...");
    connectWiFi();
    return;
  }

  if (!client || !client.connected()) {
    client = server.available();  // accept a new connection if one's waiting
    if (client) Serial.println("Client connected");
    return;
  }

  if (!client.available()) return;

  uint8_t sync0 = client.read();
  if (sync0 != 0xAA) return;

  uint8_t sync1;
  if (!readExact(client, &sync1, 1)) return;
  if (sync1 != 0x55) return;

  if (!readExact(client, frameBuf, FRAME_BYTES)) {
    Serial.println("Frame read timeout, dropping");
    return;
  }

  memcpy(display.getBuffer(), frameBuf, FRAME_BYTES);
  display.display();
}
