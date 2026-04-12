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

static