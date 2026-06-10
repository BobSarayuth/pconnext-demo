import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';
import { uuidv4 } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// Custom metrics
const responseTime = new Trend('response_time');
const successRate = new Rate('success_rate');

// Expanded list of shorter questions about SCG products and services
const question1 = [
  // ทักทาย / เริ่มต้น
  "สวัสดี",
  "สวัสดีครับ",
  "สวัสดีค่ะ",
  "หวัดดี",
  "มีใครอยู่ไหม",
  "คุยกับใครได้บ้าง",
  "ขอคำแนะนำหน่อย",
  "เริ่มยังไงดี",
  "ผมมาถามเรื่องบ้านครับ",
  "ขอสอบถามหน่อย"
]


const question2 = [
  // ติดต่อเจ้าหน้าที่
  "ขอคุยกับเจ้าหน้าที่",
  "ติดต่อเจ้าหน้าที่ได้ไหม",
  "โอนสายหน่อย",
  "อยากให้เจ้าหน้าที่โทรกลับ",
  "ขอเบอร์ติดต่อ",
  "มีพนักงานดูแลไหม",
  "ส่งต่อให้เจ้าหน้าที่หน่อย",
  "รอสายแป๊บนะ",
  "มีคนอยู่ไหม",
  "ขอให้พนักงานตอบ",

  // ค้นหาสาขา / location
  "มี SCG Digital ใกล้ฉันไหม",
  "สาขาไหนใกล้รังสิตที่สุด",
  "ร้านแถวนี้มีไหม",
  "มีสาขาในโคราชไหม",
  "อยากดูสินค้าที่สาขา",
  "หาร้านใกล้บ้าน",
  "มีโชว์รูมไหม",
  "อยากไปดูสินค้าจริง",
  "ไปที่ไหนได้บ้าง",
  "แผนที่ร้านอยู่ไหน",

  // ขอรูป / ไฟล์ / เอกสาร
  "มีรูปสินค้ารุ่นนี้ไหม",
  "ขอภาพเพิ่มเติมหน่อย",
  "ขอ catalog",
  "มีโบรชัวร์ไหม",
  "ส่งไฟล์ให้หน่อย",
  "มีคู่มือไหม",
  "ขอ datasheet",
  "ขอโหลดไฟล์ PDF",
  "มีภาพตัวอย่างไหม",
  "ขอรูปแบบติดตั้งจริง",

  // Bad Intent (ไม่สุภาพ)
  "พูดมากจัง",
  "โง่ปะเนี่ย",
  "ห่วยแตก",
  "ไปตายซะ",
  "โง่หรือเปล่า",
  "ไม่รู้ก็ไม่ต้องตอบ",
  "ไร้สาระ",
  "สาระแน",
  "เสียเวลา",
  "ไปไกลๆ",

  // ปรึกษาการใช้งาน / รีโนเวท
  "ปรึกษาเรื่องรีโนเวทได้ไหม",
  "อยากออกแบบห้องน้ำใหม่",
  "ขอใบเสนอราคา",
  "มีบริการวัดหน้างานไหม",
  "มีใครช่วยออกแบบให้ได้ไหม",
  "ขอใบประเมินราคา",
  "รับงานรีโนเวทไหม",
  "ปรึกษาการวางระบบน้ำ",
  "ปรึกษาเรื่องหลังคา",
  "อยากให้มาดูหน้างาน",

  // คำถามทั่วไป
  "ส่งสินค้าถึงเมื่อไหร่",
  "สั่งของต้องทำยังไง",
  "สินค้ามีของไหม",
  "ต้องรอนานไหม",
  "รับประกันกี่ปี",
  "มีส่วนลดไหม",
  "มีของแถมไหม",
  "ส่งต่างจังหวัดไหม",
  "มีบริการเก็บเงินปลายทางไหม",
  "คืนสินค้าได้ไหม",

  "https://m.media-amazon.com/images/I/51pEbdqMpWL._AC_SL1000_.jpg",
  "https://m.media-amazon.com/images/I/51pEbdqMpWL._AC_SL1000_.jpg",
  "https://m.media-amazon.com/images/I/51pEbdqMpWL._AC_SL1000_.jpg",
  "https://m.media-amazon.com/images/I/51pEbdqMpWL._AC_SL1000_.jpg",
  "https://scg.teemchat.net/_matrix/media/v1/download/scg.teemchat.net/fSKOXPFBwUNcAhZDTZFMBAXT",
  "https://scg.teemchat.net/_matrix/media/v1/download/scg.teemchat.net/fSKOXPFBwUNcAhZDTZFMBAXT",
  "https://scg.teemchat.net/_matrix/media/v1/download/scg.teemchat.net/fSKOXPFBwUNcAhZDTZFMBAXT",
  "https://scg.teemchat.net/_matrix/media/v1/download/scg.teemchat.net/fSKOXPFBwUNcAhZDTZFMBAXT",
  "https://cdn.pixabay.com/photo/2023/07/12/17/23/activity-8122959_640.jpg",
  "https://cdn.pixabay.com/photo/2023/07/12/17/23/activity-8122959_640.jpg",
  "https://cdn.pixabay.com/photo/2023/07/12/17/23/activity-8122959_640.jpg",
  "https://cdn.pixabay.com/photo/2023/07/12/17/23/activity-8122959_640.jpg",
];


export const options = {
  vus: 20,               // 5 virtual users
  duration: '30m',      // run for 10 minutes
  // vus: 1,            // 1 virtual user
  // iterations: 1,     // Run exactly once
  thresholds: {
    http_req_duration: ['p(95)<30000'], // 95% of requests should be below 30s
    success_rate: ['rate>0.95'],
  },
};

// Utility function to randomly select a question from a list
function randomQuestion(questions) {
  return questions[Math.floor(Math.random() * questions.length)];
}

function sendPrediction(username, question, sessionId) {
  const startTime = new Date().getTime();
  const res = http.post('http://localhost:3000/api/chat/prediction', getPayload(username, question, sessionId), params);
  responseTime.add(new Date().getTime() - startTime);
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response has valid format': (r) => r.body !== null,
  });

  if (!success) {
    console.log(`Failed request: ${res.status}, ${res.body}`);
  }
  successRate.add(success);
  return res
}

const getPayload = (username, question, sessionId) => JSON.stringify({
  question: question,
  attachments: [],
  sessionId: sessionId,
  streaming: false,
  reasoning: false
});

const params = {
  headers: {
    'Content-Type': 'application/json',
    'User-Agent': 'k6.exe@v1.0.0-rc1',
    'x-cap-api-key': 'abcd_1234',
    'x-cap-trace-id': uuidv4()
  },
};

export default function() {
  // Randomly select a username from 5 users
  const usernames = ['user1', 'user2', 'user3', 'user4', 'user5'];
  const username = usernames[Math.floor(Math.random() * usernames.length)];

  const sessionId = `${username}|${uuidv4()}`
  // Randomly select and send first question
  const q1 = randomQuestion(question1);
  sendPrediction(username, q1, sessionId);
  sleep(Math.random() * 1 + 1);

  for (let i = 0; i < Math.floor(Math.random() * 3 + 1); i++) {
    const q2 = randomQuestion(question2);
    sendPrediction(username, q2, sessionId);
    sleep(Math.random() * 1 + 1);
  }
}
