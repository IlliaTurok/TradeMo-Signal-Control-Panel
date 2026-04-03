def is_duplicate_message(last_message_by_device: dict, device_id: str, site_message_text: str):
    old_text = last_message_by_device.get(device_id)
    return bool(old_text and old_text == site_message_text)


def remember_last_message(last_message_by_device: dict, device_id: str, site_message_text: str):
    if device_id and site_message_text:
        last_message_by_device[device_id] = site_message_text
