Before flashing:

Edit WIFI_SSID and WIFI_PASS in the sketch to your actual network credentials.
Both the ESP32 and your PC need to be on the same WiFi network — this won't work across different networks (e.g. phone hotspot vs. home WiFi) without extra port-forwarding you don't need here.
Flash it, then open Arduino IDE's Serial Monitor (115200 baud) once — it prints the IP address it got via DHCP. Write that down.
Run: python playback_wifi.py output.bin <that_IP> 3333
