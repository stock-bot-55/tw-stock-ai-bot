# Telegram 與 GitHub 免費部署設定教學

作者：**Manus AI**

本文件說明如何把台股選股工具接到 Telegram，並部署到 GitHub Actions，讓你的電腦關機後仍能自動執行早報、盤中提醒與晚報。

## 一、取得 Telegram Bot Token

請在 Telegram 搜尋 **BotFather**，輸入 `/newbot`，依照提示設定 Bot 名稱與使用者名稱。建立完成後，BotFather 會給你一組 Token，格式通常像 `123456789:AA...`。這組 Token 等同於機器人的密碼，不要貼到公開聊天室，也不要寫死在程式碼裡。

## 二、取得 Telegram Chat ID

先把你剛建立的 Bot 加入你要接收通知的聊天室，或直接打開與 Bot 的對話並傳一句話。接著在瀏覽器打開以下網址，將 `<TOKEN>` 換成你的 Bot Token。

```text
https://api.telegram.org/bot<TOKEN>/getUpdates
```

頁面回傳的 JSON 中會有 `chat`，裡面的 `id` 就是 Chat ID。如果你使用群組，Chat ID 通常會是負數。若看不到資料，請先傳訊息給 Bot，再重新整理網址。

## 三、設定 GitHub Secrets

請到你的 GitHub Repository，依序進入 **Settings → Secrets and variables → Actions → New repository secret**，新增以下兩個 Secrets。

| Secret 名稱 | 內容 |
|---|---|
| `TG_BOT_TOKEN` | BotFather 給你的 Telegram Bot Token |
| `TG_CHAT_ID` | 你要接收推播的聊天室 ID |

完成後，GitHub Actions 執行時會自動把這兩個值注入程式。這樣做的好處是程式碼可以公開，但敏感資訊不會外洩。

## 四、手動測試

進入 Repository 的 **Actions** 頁面，選擇 `TW Stock AI Bot`，按下 **Run workflow**。你可以選擇 `morning`、`intraday` 或 `evening`。如果設定正確，Telegram 會收到一則測試報告。

## 五、常見問題

如果沒有收到訊息，請先確認 Bot 是否已加入聊天室、Chat ID 是否正確、Secrets 名稱是否完全相同。若 GitHub Actions 顯示資料抓取失敗，通常是外部資料源暫時異常，系統會優先使用快取；若完全沒有快取，則需要等下一次排程重試。
