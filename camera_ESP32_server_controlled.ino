#include "esp_camera.h"
#include <WiFi.h>
#include <Wire.h>

// defining camera pins
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// Wifi Credentials go here
char ssid[] = ""; // fills these in with the WiFi networks name and password then upload to the ESP32-cam
char pass[] = "";

int status = WL_IDLE_STATUS;
IPAddress server(192,168,1,100);
int port = 25425;

WiFiClient client;
String mac;

WiFiUDP udp;
IPAddress broadcastIP(192,168,1,255); // this may need to be changed depending on how the WiFi network is configured

/*
 * If this device is unable to connect to the server, it will do a udp broadcast asking for the servers IP.
 * If the server is available it will respond with the correct IP address.
 */
void findServer()
{
  String message = "brain address?";
  
  udp.beginPacket(broadcastIP, 25426);
  for (int x = 0; x < message.length(); x++)
  {
    udp.write(message[x]);
  }
  udp.endPacket();

  delay(1000);

  String response;
  int packetSize = udp.parsePacket();
  if (packetSize)
  {
    while (udp.available())
      response += (char)udp.read();

    String responseFront = response.substring(0, 14);
    Serial.println(responseFront);
    if (responseFront == "brain address:")
    {
      response = response.substring(14);
      Serial.println(response);
      uint8_t zero = (uint8_t)response.substring(0,3).toInt();
      uint8_t one = (uint8_t)response.substring(4,7).toInt();
      uint8_t two = (uint8_t)response.substring(8,9).toInt();
      uint8_t three = (uint8_t)response.substring(10).toInt();
      server[0] = zero;
      server[1] = one;
      server[2] = two;
      server[3] = three;
    }
  }
  delay(2000);
}

/*
 * Initiates a TCP connection with the server and sends this devices MAC address
 */
void connectToServer()
{
  Serial.println("Connecting to Server");
  while (!client.connect(server, port))
  {
    Serial.print("Failed to connect to server at ");
    Serial.print(server);
    Serial.println(", asking for server IP, will retry in 3 seconds");
    findServer();
  }
  Serial.println("Server Connected");

  Serial.println("Sending this devices MAC address");
  client.print(mac);
  delay(1000);
}

/*
 * Prepares the ESP32 by connecting to wifi and initializing the camera
 */
void setup() 
{
  Serial.begin(115200);
  
  Serial.println("Connecting to WiFi");
  WiFi.begin(ssid, pass);
  int count = 0;
  while (WiFi.status() != WL_CONNECTED)
  {
    Serial.print(".");
    delay(1000);
    if (count == 5)
    {
      count = 0;
      WiFi.begin(ssid, pass);
    }
    count++;
  }
  Serial.println();
  Serial.println("WiFi Connected");

  mac = String(WiFi.macAddress());
  
  // initialize camera, config settings are copied from example documetation here: https://github.com/espressif/esp32-camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 2; //lower is higher quality
  config.fb_count = 1;
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK)
  {
    Serial.println("Camera initialization failed");
    while(1);
  }

  sensor_t * sensor = esp_camera_sensor_get();
  sensor -> set_brightness(sensor, 0); // -2 - 2
  sensor -> set_contrast(sensor, 1);
  //sensor -> set_saturation(sensor, 0);
  //sensor -> set_special_effect(sensor, 0);
  sensor -> set_whitebal(sensor, 1); // default was 1
  sensor -> set_awb_gain(sensor, 0); // default was 1
  sensor -> set_wb_mode(sensor, 4); // default was 0
  sensor -> set_exposure_ctrl(sensor, 0); // default was 1
  sensor -> set_aec2(sensor, 0);
  sensor -> set_ae_level(sensor, 0);
  sensor -> set_aec_value(sensor, 1200); // manual exposure 0 - 1200
  sensor -> set_gain_ctrl(sensor, 0);
  sensor -> set_agc_gain(sensor, 0);
  //sensor -> set_gainceiling(sensor, (gainceiling_t)0);
  sensor -> set_bpc(sensor, 0);
  sensor -> set_wpc(sensor, 1);
  //sensor -> set_raw_gma(sensor, 1);
  //sensor -> set_lenc(sensor, 1);
  //sensor -> set_hmirror(sensor, 0);
  //sensor -> set_vflip(sensor, 0);
  //sensor -> set_dcw(sensor, 1);
  //sensor -> set_colorbar(sensor, 0);
  
  
  Serial.println("Setup complete");
  delay(100);
}

/*
 * Main loop, this runs continuously.
 * First it connects to the server.
 * Second it captures an image.
 * Third it checks if the server wants an image.
 * Fourth it sends the image to the server.
 * Repeat forever.
 */
void loop() 
{
  if (!client.connected())
  {
    connectToServer();
  }

  //Capture Image
  camera_fb_t * frameBuffer = esp_camera_fb_get();
  
  //Serial.println("Waiting for image request");
  if (client.available())
  {
    client.flush();
    
    // capture an image
    if (!frameBuffer)
    {
      Serial.println("Failed to capture image");
      // kills the connection if something goes wrong so that the server doesn't wait forever
      client.stop();
    }
    else
    {
      // send the image to the server
      Serial.println("Sending image to server");
      client.write(frameBuffer->buf, frameBuffer->len);
      //esp_camera_fb_return(frameBuffer);
    }
  }
  esp_camera_fb_return(frameBuffer);
}
