import requests
import json
import pprint
import datetime
import logging
import pytz

#######################################################################################################
# Format URLs
VZ_GET_URL = "http://vz.wiuhelmtell.ch/middleware.php/data/{}.json?from={}"
VZ_POST_URL = "http://vz.wiuhelmtell.ch/middleware.php/data/{}.json?operation=add&value={}"
########################################################################################################

#######################################################################################################
# Configuration
UUID = {
    "T_outdoor": "8f471ab0-1cab-11e9-8fa4-3b374d3c10ca",
    "Power_balance": "9b251460-35ae-11e9-ba29-959207ffefe4",
    "Charge_station": "8270f520-6690-11e9-9272-4dde30159c8f",
    "Freigabe_sonderbetrieb": "e7e6d7e0-d973-11e9-841d-0597e49a80a1",
    "Freigabe_excess": "90212900-d972-11e9-910d-078a5d14d2c9",
    "Sperrung_excess": "dd2e3400-d973-11e9-b9c6-038d9113070b",
    "Freigabe_normalbetrieb": "fc610770-d9fb-11e9-8d49-5d7c9d433358",
}

FREIGABE_WARM_TEMP = 15
FREIGABE_KALT_TEMP = -10
FREIGABE_NORMAL_TEMP = 19

FREIGABE_WARM_P = 800
FREIGABE_KALT_P = 2500

UHRZEIT_WARM = datetime.time(18, 0)
UHRZEIT_KALT = datetime.time(18, 0)

SPERRUNG_SONDERBETRIEB = 200
###########################################################################################################

def get_vals(uuid, duration="-0min"):
    req = requests.get(VZ_GET_URL.format(uuid, duration))
    #return(json.loads(req.content))
    return req.json()

def write_vals(uuid, val):
    poststring = VZ_POST_URL.format(uuid, val)
    logging.info("Poststring {}".format(poststring))
    postreq = requests.post(poststring)
    logging.info("Ok? {}".format(postreq.ok))

def get_freigabezeit_12h_temp(t_roll_avg):
    u_w = UHRZEIT_WARM.hour + UHRZEIT_WARM.minute / 60
    u_k = UHRZEIT_KALT.hour + UHRZEIT_KALT.minute / 60
    f_time = u_w + (t_roll_avg - FREIGABE_WARM_TEMP) * (
        (u_w - u_k) / (FREIGABE_WARM_TEMP - FREIGABE_KALT_TEMP))
    logging.info("Decimal Unlocktime: {}".format(f_time))
    f_time_12h_temp = datetime.time(
        hour=int(f_time), minute=int((f_time - int(f_time))*60))
    logging.info("DMS Unlocktime: {}".format(f_time_12h_temp))
    return(f_time_12h_temp)


def get_freigabezeit_excess(t_now):
    p_unlock_now = -(FREIGABE_WARM_P + (t_now - FREIGABE_WARM_TEMP) * (
        (FREIGABE_WARM_P - FREIGABE_KALT_P)/(FREIGABE_WARM_TEMP - FREIGABE_KALT_TEMP)))
    logging.info("Freigabe Leistung: {}".format(p_unlock_now))
    return p_unlock_now


def main():
    tz = pytz.UTC
    b_freigabe_12h_temp = 0
    b_freigabe_excess = 0
    b_sperrung_excess = 0
    b_freigabe_normal = 0
    logging.basicConfig(level=logging.INFO)
    logging.info("*****************************")
    logging.info("*Starting WP controller")
    now = datetime.datetime.now(tz=tz)
    logging.info("UTC time: {}".format(now))
    logging.info("*****************************")
    logging.info("Get values from VZ")
    t_now = get_vals(UUID["T_outdoor"])["data"]["tuples"][0][1]
    t_roll_avg_12 = get_vals(
        UUID["T_outdoor"], duration="-720min")["data"]["average"]
    t_roll_avg_24 = get_vals(
        UUID["T_outdoor"], duration="-1440min")["data"]["average"]
    power_balance = get_vals(
        UUID["Power_balance"], duration="-15min")["data"]["average"]
    p_charge = get_vals(UUID["Charge_station"],
                        duration="-15min")["data"]["average"]
    p_net = power_balance - p_charge
    logging.info(p_net)

    
    f_time_12h_temp = get_freigabezeit_12h_temp(t_roll_avg_12)
    if now.time() > f_time_12h_temp:
        b_freigabe_12h_temp = 1
    if t_roll_avg_24 < FREIGABE_NORMAL_TEMP:
        b_freigabe_normal = 1
    logging.info("Freigabe Zeit: {}".format(b_freigabe_12h_temp))
    write_vals(UUID["Freigabe_sonderbetrieb"], b_freigabe_12h_temp)
    logging.info("******************************")
    logging.info("P_Excess")
    p_freigabe_now = get_freigabezeit_excess(t_now)
    if p_net < p_freigabe_now:
        b_freigabe_excess = 1
    if p_net > SPERRUNG_SONDERBETRIEB:
        b_sperrung_excess = 1
    logging.info("Freigabe Excess: {}".format(b_freigabe_excess))
    logging.info("Sperrung Excess: {}".format(b_sperrung_excess))
    write_vals(UUID["Freigabe_excess"], b_freigabe_excess)
    write_vals(UUID["Sperrung_excess"], b_sperrung_excess)
    logging.info("********************************")
    if (b_freigabe_normal & b_freigabe_12h_temp & b_freigabe_excess):
        logging.info("Ich würde die Anlage jetzt freigeben")
    if b_sperrung_excess:
        logging.info("Ich würde die Anlage jetzt Sperren")


if __name__ == "__main__":
    main()