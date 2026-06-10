# 🏠 SCG Digital AI Service (Bobby)

[![SCG Digital AI Dev](https://img.shields.io/badge/SCG%20Home%20AI-Developer-blue)](https://github.com/scg-wedo/cap-scg-digital-ai-service)
[![Python](https://img.shields.io/badge/Python-3.12-success?logo=python)](https://www.python.org/)


## 📋 Overview

SCG Digital AI Service (Bobby) is an intelligent conversational agent designed to assist customers with inquiries about SCG Digital building materials, products, and services. The system leverages advanced AI models to provide accurate information about products, pricing, installation guidance, and other related topics.

## ✨ คุณสมบัติเด่น

- **🗣️ คุยได้เหมือนคน**: โต้ตอบกับผู้ใช้เรื่องวัสดุก่อสร้างและการปรับปรุงบ้านด้วยภาษาธรรมชาติ
- **🛒 ข้อมูลผลิตภัณฑ์**: แสดงรายละเอียดสินค้า SCG ทั้งสเปค ราคา และสถานะสินค้า
- **🤖 รองรับหลายโมเดล AI**: ใช้งานได้ทั้ง Google Gemini และ OpenAI
- **⚡ ตอบแบบ Streaming**: แสดงคำตอบแบบเรียลไทม์พร้อมเหตุผลการคิดวิเคราะห์
- **💬 จัดการบทสนทนา**: เก็บประวัติการสนทนาต่อเนื่อง

## 🏗️ สถาปัตยกรรม

ระบบประกอบด้วยไมโครเซอร์วิสหลัก:

- **🧠 scgdigital-api**: บริการ AI หลักประมวลผลคำถามและสร้างคำตอบ
- **📊 common-content-api**: จัดการข้อมูลสินค้า
- **🌐 agentic-chat**: ส่วนติดต่อผู้ใช้แบบเว็บ
- **🔄 redis**: แคชจัดการเซสชันและเพิ่มประสิทธิภาพ
- **💾 postgres**: ฐานข้อมูลเก็บประวัติสนทนา

## 🚀 การติดตั้งสำหรับนักพัฒนา

### 🔧 ความต้องการเบื้องต้น

- 🐳 Docker และ Docker Compose
- 🔑 LiteLLM API access
- 🔐 SCG Content Service API key
- 🐍 Python 3.12+ (สำหรับ SCG-HOME AI)
- 🐢 Conda (แนะนำสำหรับจัดการสภาพแวดล้อม)

#### 🏁 เริ่มต้นใช้งาน

1. สร้างและเปิดใช้งานสภาพแวดล้อม Python:
   ```bash
   conda create -p .venv python=3.12
   conda activate .venv
   pip install -r requirements.txt -r requirements-dev.txt
   ```

2. ติดตั้งส่วนขยาย VSCode ที่แนะนำ:
   - ค้นหา `@recommended` ในแถบ Extensions
   - ติดตั้งทั้งหมดตามคำแนะนำ

3. ตั้งค่า commit message สำหรับ Jira:
   ```bash
   pre-commit install
   commit-linter install
   curl https://raw.githubusercontent.com/dvgamerr/commit-linter-jira/refs/heads/main/commit_linter/hooks/commit-msg -o .git/hooks/commit-msg
   ```

### ⚙️ ตั้งค่าสภาพแวดล้อม

1. โคลนโปรเจคและส่วนที่เกี่ยวข้อง:
   ```bash
   git clone https://github.com/scg-wedo/cap-agentic-chat-ui.git
   git clone https://github.com/scg-wedo/cap-common-content-service.git

   touch ./cap-agentic-chat-ui/.env
   touch ./cap-common-content-service/.env

   # check latest version
   git checkout <version>
   ```
2. รับไฟล์ .env ที่มีค่า secrets ต่างๆ:
- ติดต่อขอไฟล์ .env จาก project lead
- ไฟล์นี้มีค่า API keys และการตั้งค่าที่จำเป็นสำหรับการพัฒนา

#### ▶️ เริ่มใช้งาน SCG-HOME AI

เริ่มบริการ SCG-HOME AI:
   ```bash
   python main.py
   ```

ล้างสภาพแวดล้อม (หากจำเป็น):
   ```bash
   conda remove -n .venv --all
   ```

---

## 👨‍💻 Developers

<table>
  <tr>
    <td align="center" width="50%">
      <a href="https://github.com/dvgamerr">
        <img src="https://github.com/dvgamerr.png" width="100px;" alt="dvgamerr"/><br />
        <sub><b>Kananek T. (dvgamerr)</b></sub>
      </a><br />
      <a href="https://wakatime.com/badge/user/06633b1c-3ba7-44c2-ab5d-08e47ccc87ab/project/a5501782-605e-4d7d-b808-9a0f8e17c9c1">
         <img src="https://wakatime.com/badge/user/06633b1c-3ba7-44c2-ab5d-08e47ccc87ab/project/a5501782-605e-4d7d-b808-9a0f8e17c9c1.svg" alt="Time spent coding" />
      </a>
    </td>
    <td align="center" width="50%">
      <a href="https://github.com/ChayaTun">
        <img src="https://github.com/ChayaTun.png" width="100px;" alt="ChayaTun"/><br />
        <sub><b>Chayakorn T. (ChayaTun)</b></sub>
      </a><br />
      <a href="https://wakatime.com/badge/user/5d2cd0f7-2d1e-45c0-bb20-3045f67fc48b/project/736263fe-5389-4f6e-8541-0a105d98e3e9">
         <img src="https://wakatime.com/badge/user/5d2cd0f7-2d1e-45c0-bb20-3045f67fc48b/project/736263fe-5389-4f6e-8541-0a105d98e3e9.svg" alt="Time spent coding" />
      </a>
    </td>
  </tr>
</table>
