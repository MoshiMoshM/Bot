# 🎵 Discord Music Bot

## Команди
| Команда | Описание |
|---------|----------|
| `!play <песен/линк>` | Пусни музика от YouTube |
| `!skip` | Пропусни песента |
| `!stop` | Спри музиката |
| `!pause` | Паузирай/продължи |
| `!queue` | Виж опашката |
| `!np` | Сега свири |
| `!volume <1-100>` | Промени звука |
| `!help` | Помощ |

## Деплой в Railway

1. Качи файловете в GitHub репо
2. Railway → New Project → Deploy from GitHub repo
3. Variables → Add Variable:
   - Key: `DISCORD_TOKEN`
   - Value: твоят бот токен
4. Railway автоматично ще пусне бота ✅
