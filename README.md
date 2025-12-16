# 🎮 My Paper Minecraft Server

24/7 Paper Minecraft server with Geyser (Bedrock support) deployed on Railway.

## 🔌 Installed Plugins

- **Geyser + Floodgate** - Bedrock player support
- **AdvancedTeleport** - Teleportation commands
- **VeinMining** - Mine entire veins at once
- **TreeFeller** - Chop entire trees
- **Spark** - Performance monitoring

## 🚀 Deploy to Railway

1. Push this folder to GitHub
2. Go to [railway.app](https://railway.app)
3. New Project → Deploy from GitHub repo
4. Select this repository
5. Enable Public Networking (port 25565 for Java, 19132 for Bedrock)

## ⚙️ Environment Variables

Set these in Railway dashboard to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMORY_MIN` | `1G` | Minimum RAM |
| `MEMORY_MAX` | `2G` | Maximum RAM |

## 🌐 Connecting

### Java Edition
Use the Railway public URL (e.g., `your-server.railway.app`)

### Bedrock Edition
Use the same URL with port `19132`

## 📁 Server Structure

```
├── world/           # Overworld
├── world_nether/    # Nether
├── world_the_end/   # End
├── plugins/         # All plugins + configs
├── server.jar       # Paper server
└── server.properties
```

---
Made with ❤️ for Minecraft
