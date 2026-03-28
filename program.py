from telethon import TelegramClient, events

api_id = 37853433      # твой api_id
api_hash = '2b593ec952b6dc6134f101d599f8600a' # твой api_hash
session_name = 'TradeMo Bot'   # имя файла сессии
chat = 'trademo_sup_bot'        # @username бота уведомлений или ID чата

TARGET_TEXTS = [
    'disabled',
]      # то, что считаем сигналом

def on_signal(event):
    # тут твой код реакции
    print('СИГНАЛ ПОЛУЧЕН!', event.message.text)
    # пример: дергаем своего бота через HTTP, пишем в файл, запускаем стратегию и т.п.

client = TelegramClient(session_name, api_id, api_hash)

@client.on(events.NewMessage(chats=chat))
async def handler(event):
    text = (event.raw_text or '').upper()
    targets_upper = [t.upper() for t in TARGET_TEXTS]
    if any(t in text for t in targets_upper):
        on_signal(event)

client.start()
print('Жду сигналы...')
client.run_until_disconnected()