/*

decr : sensor abstraction layer
        reads from :
            - ADS1115 (16-bit ADC ) for analog sensors
            - MPU6050 ( IMU over I2C ) for vibration/ motion
            - Internal ESP32 ADC
            Fuses reading into a single normalised 16-bit word
            that the pipeline CPU can operate on directly
            
*/

#include <string.h>
#include "sensor.h"
#include "driver/i2c.h"
#include "driver/adc.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define TAG "SENSOR"

/*  I2C bus configuration */
#define I2C_MASTER_NUM              I2C_NUM_0     
#define I2C_MASTER_SCL_IO           22         
#define I2C_MASTER_SDA_IO           21          
#define I2C_MASTER_FREQ_HZ          400000
#define I2C_TIMEOUT_MS               1000      

/* ADS1115 configuration */
#define ADS1115_ADDR                0x48
#define ADS1115_REG_CONV      0x00
#define ADS1115_REG_CFG          0x01

/* Config : AIN0-GND, +-4.096 V FSR,  128 SPS , Single -shot */
#define ADS1115_CFG_HI          0xC3
#define ADS1115_CFG_LO          0x83

/* MPU6050 configuration */
#define MPU6050_ADDR               0x68
#define MPU6050_REG_PWR            0x6B
#define MPU6050_REG_ACCEL_X        0x3B


/* Internal ADC (fallback)*/
#define ADC_CHANNEL         ADC1_CHANNEL_6
#define ADC_WIDTH           ADC_WIDTH_BIT_12

static  bool ads1115_ok  = false ;
static  bool mpu6050_ok  = false ;

/* I2C helpers*/

static esp_err_t i2c_write_reg ( uint8_t addr, uint8_t reg,
                                const uint8_t *data, size_t len)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create() ;
    i2c_master_start(cmd) ;
    i2c_master_write_byte(cmd, (addr << 1 )  |  I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true) ;
    i2c_master_write(cmd, data, len, true) ;
    i2c_master_stop(cmd) ;
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd,
                                         pdMS_TO_TICKS(I2C_TIMEOUT_MS) ) ;
    i2c_cmd_link_delete(cmd) ;
    return ret ;
}                                

static esp_err_t i2c_read_reg(uint8_t addr, uint8_t reg, 
                              const uint8_t *buff, size_t len)
{
    i2c_cmd_handle_t cmd = i2c_cmd_link_create() ;
    i2c_master_start(cmd);
    i2c_master_write_byte(cmd, (addr << 1 ) | I2C_MASTER_WRITE, true);
    i2c_master_write_byte(cmd, reg, true) ;
    i2c_master_start(cmd) ;
    i2c_master_write_byte(cmd, (addr << 1 ) | I2C_MASTER_READ, true);
    if ( len > 1 ) 
        i2c_master_read(cmd, buff, len - 1, I2C_MASTER_ACK);
    i2c_master_read_byte(cmd, buff + len - 1, I2C_MASTER_NACK) ;
    i2c_master_stop(cmd) ;
    esp_err_t ret = i2c_master_cmd_begin(I2C_MASTER_NUM, cmd,
                                         pdMS_TO_TICKS(I2C_TIMEOUT_MS) ) ;
    i2c_cmd_link_delete(cmd) ;
    return ret ;
}

/* ADS1115 trigger single shot & read 16bit result*/
static int16_t ads1115_read_channel0(void)
{ 
    /* trigger single-shot conversion */
    uint8_t cfg[2] = {ADS1115_CFG_HI, ADS1115_CFG_LO};
    if (i2c_write_reg(ADS1115_ADDR, ADS1115_REG_CFG, cfg, 2) != ESP_OK)
        return -1:
    
    /* wait for conversion (-8 ms at 128 SPS)*/
    vTaskDelay(pdMS_TO_TICKS(10)) ;
    /* read 16 bit result */
    uint8_t raw[2] = {0};
    if (i2c_read_reg(ADS1115_ADDR, ADS1115_REG_CONV, raw, 2) != ESP_OK)
        return -1;
    return (int16_t)((raw[0] << 8) | raw[1]) ;

}

/*MPU6050- read accelerometer  X magnitude*/
static int16_t mpu6050_vibration(void)
{
    uint8_t raw[6] = {0};
    if (i2c_read_reg(MPU6050_ADDR, MPU6050_REG_ACCEL_X, raw, 6) != ESP_OK)
        return 0;
    
        int16_t ax = (int16_t)((raw[0] << 8) | raw[1]) ;
        int16_t ay = (int16_t)((raw[2] << 8) | raw[3]) ;
        int16_t az = (int16_t)((raw[4] << 8) | raw[5]) ;

        int16_t mag = abs(ax) ;
        if (abs(ay) > mag) mag = abs(ay);
        if (abs(az) > mag) mag = abs(az);
        return (uint16_t)mag ;

}

/* sensor init*/
void sensor_init(void)
{
    /* I2C init */
    i2c_config_t conf = {
        .mode = I2C_MODE_MASTER,
        .sda_io_num = I2C_MASTER_SDA_IO,
        .scl_io_num = I2C_MASTER_SCL_IO,
        .sda_pullup_en = GPIO_PULLUP_ENABLE,
        .scl_pullup_en = GPIO_PULLUP_ENABLE,
        .master.clk_speed = I2C_MASTER_FREQ_HZ
    };
    i2c_param_config(I2C_MASTER_NUM, &conf);
    i2c_driver_install(I2C_MASTER_NUM, conf.mode, 0, 0, 0);

    /* Check ADS1115 */
    uint8_t dummy[2] ;
    if (i2c_read_reg(ADS1115_ADDR, ADS1115_REG_CFG, dummy, 2) == ESP_OK) {
        ads1115_ok = true ;
        ESP_LOGI(TAG, "ADS1115 detected");
    } else {
        ESP_LOGW(TAG, "ADS1115 not detected");
    }

    /* Check MPU6050 */
    uint8_t wake = 0x00;
    if (i2c_write_reg(MPU6050_ADDR, MPU6050_REG_PWR, &wake, 1) == ESP_OK) {
        mpu6050_ok = true ;
        ESP_LOGI(TAG, "MPU6050 detected");
    } else {
        ESP_LOGW(TAG, "MPU6050 not detected");
    }


    /* Internal ADC init */
    adc1_config_width(ADC_WIDTH);
    adc1_config_channel_atten(ADC_CHANNEL, ADC_ATTEN_DB_11);

    ESP_LOGI(TAG, "Sensor subsystem ready");
}

/* sensor_read16bit
   returns a fused 16 b sensor word :
        [15:8] = Primary channel ( ADS1115 high byte or ADC)
        [7:0] = Secondary ( vibration mag from MPU6050 or 0)

*/

uint16_t sensor_read16bit(void)
{
    uint16_t primary = 0 ;
    uint8_t secondary = 0 ;

    if ( ads1115_ok) {
        int16_t adc_val = ads1115_read_channel0() ;
        if ( adc_val < 0) adc_val = 0;
        /* Scale 0-32767 -> 0-65535 for full 16-b range*/
        primary = (uint16_t)((uint32_t)adc_val * 2);
    } else {
        /*internal 12-b ADC -> scale to 16bit*/
        int raw = adc1_get_raw(ADC_CHANNEL);
        primary = (uint16_t)((uint32_t)raw * 16); 
    }
     
    /* secondary : MPU6050 vibration*/
    if (mpu6050_ok) {
        secondary = mpu6050_vibration() >> 8 ; 
        if (secondary > 255) secondary = 255;

    }

    /* Fuse : primary occupies [15:8], secondary [7:0]*/
    uint16_t fused = (primary & 0xFF00) | (secondary & 0x00FF) ;

    ESP_LOGD(TAG, "primary=%u  secondary=%u  fused=0x%04X",
             primary, secondary, fused);

    return fused;
}


