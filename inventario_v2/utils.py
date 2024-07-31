days_names = {
    0: "Lun",
    1: "Mar",
    2: "Mié",
    3: "Jue",
    4: "Vie",
    5: "Sáb",
    6: "Dom",
}


def get_day_name(day_number):
    return days_names.get(day_number, "Día no válido")
