const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const { DisTube } = require('distube');
const { YtDlpPlugin } = require('@distube/yt-dlp');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildVoiceStates,
  ],
});

const distube = new DisTube(client, {
  plugins: [new YtDlpPlugin()],
});

const PREFIX = '!';

client.once('ready', () => {
  console.log(`✅ Logged in as ${client.user.tag}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot || !message.content.startsWith(PREFIX)) return;

  const args = message.content.slice(PREFIX.length).trim().split(/ +/);
  const command = args.shift().toLowerCase();

  const voiceChannel = message.member?.voice?.channel;

  if (command === 'play' || command === 'p') {
    if (!voiceChannel) {
      return message.reply('❌ Трябва да си в гласов канал!');
    }
    const query = args.join(' ');
    if (!query) return message.reply('❌ Напиши песен или YouTube линк!');

    try {
      await distube.play(voiceChannel, query, {
        textChannel: message.channel,
        member: message.member,
      });
    } catch (err) {
      message.reply(`❌ Грешка: ${err.message}`);
    }
  }

  else if (command === 'skip' || command === 's') {
    const queue = distube.getQueue(message.guild);
    if (!queue) return message.reply('❌ Няма нищо в опашката!');
    try {
      await queue.skip();
      message.reply('⏭️ Пропуснато!');
    } catch {
      message.reply('❌ Няма следваща песен!');
    }
  }

  else if (command === 'stop') {
    const queue = distube.getQueue(message.guild);
    if (!queue) return message.reply('❌ Нищо не свири!');
    queue.stop();
    message.reply('⏹️ Спряно!');
  }

  else if (command === 'pause') {
    const queue = distube.getQueue(message.guild);
    if (!queue) return message.reply('❌ Нищо не свири!');
    if (queue.paused) {
      queue.resume();
      message.reply('▶️ Продължено!');
    } else {
      queue.pause();
      message.reply('⏸️ Паузирано!');
    }
  }

  else if (command === 'queue' || command === 'q') {
    const queue = distube.getQueue(message.guild);
    if (!queue) return message.reply('❌ Опашката е празна!');

    const songs = queue.songs
      .slice(0, 10)
      .map((s, i) => `${i === 0 ? '▶️' : `${i}.`} **${s.name}** — ${s.formattedDuration}`)
      .join('\n');

    const embed = new EmbedBuilder()
      .setTitle('🎵 Опашка')
      .setDescription(songs)
      .setColor(0x5865F2);

    message.reply({ embeds: [embed] });
  }

  else if (command === 'volume' || command === 'v') {
    const queue = distube.getQueue(message.guild);
    if (!queue) return message.reply('❌ Нищо не свири!');
    const vol = parseInt(args[0]);
    if (isNaN(vol) || vol < 1 || vol > 100) return message.reply('❌ Въведи число между 1 и 100!');
    queue.setVolume(vol);
    message.reply(`🔊 Сила на звука: ${vol}%`);
  }

  else if (command === 'np' || command === 'nowplaying') {
    const queue = distube.getQueue(message.guild);
    if (!queue) return message.reply('❌ Нищо не свири!');
    const song = queue.songs[0];
    const embed = new EmbedBuilder()
      .setTitle('🎵 Сега свири')
      .setDescription(`**${song.name}**\n⏱️ ${queue.formattedCurrentTime} / ${song.formattedDuration}`)
      .setThumbnail(song.thumbnail)
      .setColor(0x5865F2);
    message.reply({ embeds: [embed] });
  }

  else if (command === 'help') {
    const embed = new EmbedBuilder()
      .setTitle('🎵 Муз Бот — Команди')
      .setDescription([
        '`!play <песен/линк>` — Пусни музика',
        '`!skip` — Пропусни песента',
        '`!stop` — Спри музиката',
        '`!pause` — Паузирай/продължи',
        '`!queue` — Виж опашката',
        '`!np` — Виж текущата песен',
        '`!volume <1-100>` — Промени звука',
      ].join('\n'))
      .setColor(0x5865F2);
    message.reply({ embeds: [embed] });
  }
});

// DisTube events
distube.on('playSong', (queue, song) => {
  const embed = new EmbedBuilder()
    .setTitle('🎵 Сега свири')
    .setDescription(`**[${song.name}](${song.url})**\n⏱️ Продължителност: ${song.formattedDuration}`)
    .setThumbnail(song.thumbnail)
    .setColor(0x5865F2)
    .setFooter({ text: `Поискано от ${song.member?.displayName}` });
  queue.textChannel?.send({ embeds: [embed] });
});

distube.on('addSong', (queue, song) => {
  queue.textChannel?.send(`✅ Добавено: **${song.name}** (${song.formattedDuration})`);
});

distube.on('error', (channel, error) => {
  console.error('DisTube error:', error);
  channel?.send(`❌ Грешка: ${error.message}`);
});

client.login(process.env.DISCORD_TOKEN);
