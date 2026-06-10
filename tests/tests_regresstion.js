import http from 'k6/http'
import { check, sleep } from 'k6'
import { Trend, Rate } from 'k6/metrics'
import { SharedArray } from 'k6/data'
import papaparse from './k6/papaparse.min.js';
// Custom metrics
const responseTime = new Trend('response_time')
const successRate = new Rate('success_rate')

const BASEURL = __ENV.K6_BASEURL || 'http://localhost:3081'
const VUS_MAX = __ENV.K6_VUS_MAX || 15
const CSV_FILE = __ENV.K6_CSV_FILE || './tests_regresstion.csv'

const getIterations = (totalVUs, total) => ({
  vus: Math.floor(totalVUs),
  iterations: Math.ceil(total / totalVUs)
})

const splitGroupVUs = (VUs, totalVUs, data) => {
  const groupSize = Math.ceil(data.length / totalVUs);
  const startIndex = (VUs - 1) * groupSize;
  const endIndex = startIndex + groupSize;
  return data.slice(startIndex, endIndex);
}

const queryUnittests = new SharedArray("regression tests", () => {
  try {
    return papaparse.parse(open(CSV_FILE), { header: true }).data;
  } catch (ex) {
    throw new Error(`Error loading CSV from file: ${ex.message}`)
  }
})


const parallel = getIterations(VUS_MAX, queryUnittests.length)

export const options = {
  // Set up parallel execution based on session IDs
  scenarios: {
    parallel_sessions: {
      executor: 'per-vu-iterations',
      vus: parallel.vus,
      iterations: parallel.iterations,
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<15000'], // 95% of requests should be below 20s
    success_rate: ['rate>0.95'],     // 95% success rate
  },
}

const sessionList = []
export function setup() {
  const testOptions = options.scenarios.getSortedConfigs()[0]

  return { testOptions };
}


export default function(data) {
  // Get the assigned portion of test cases for this VU
  const vuTests = splitGroupVUs(__VU, data.testOptions.vus, queryUnittests);
  const testCase = vuTests[__ITER % vuTests.length];

  // Check if we have test data
  if (!vuTests.length || !testCase?.['ActualQuery']) {
    sleep(3);
    return;
  }

  // Randomly select a username
  const usernames = [
    'Alice', 'Bob', 'Charlie', 'Diana', 'Eve', 'Frank',
    'Grace', 'Hank', 'Ivy', 'Jack', 'Karen', 'Leo',
    'Mona', 'Nina', 'Oscar', 'Paul', 'Quincy', 'Rachel',
    'Steve', 'Tina', 'Uma', 'Victor', 'Wendy', 'Xander',
    'Yara', 'Zane'
  ];
  const username = usernames[(__VU - 1) % usernames.length];

  console.log(`HM: [${testCase['ID'].padEnd(3)}] ${username.padEnd(9)}, Iters : ${__ITER}`);

  const IsImage = testCase['ActualQuery'].trim().startsWith('http');

  const payload = JSON.stringify({
    question: IsImage ? '' : testCase['ActualQuery'].trim(),
    attachments: IsImage ? [testCase['ActualQuery'].trim()] : [],
    sessionId: testCase['Session'],
    username: username,
    streaming: false,
    reasoning: false
  });

  const options = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-test',
      'x-cap-api-key': 'abcd_1234'
    },
  }

  const startTime = new Date().getTime();
  const res = http.post(`${BASEURL}/api/chat/prediction`, payload, options);
  const endTime = new Date().getTime();

  // // Record response time
  responseTime.add(endTime - startTime);

  // Check if response is valid
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response has valid format': (r) => r.body !== null
  });

  successRate.add(success);

  // Log details for debugging
  if (!success) {
    console.log(`Failed request: ${res.status}, ${res.body}`);
  }
}

export function teardown() {
  for (const test of queryUnittests) {
    const deleteRes = http.del(`${BASEURL}/api/chat/${test["Session"]}`, null, options);

    check(deleteRes, {
      'session cleanup successful': (r) => r.status >= 200 && r.status < 300,
    });

    if (deleteRes.status !== 200) {
      console.log(`Failed to clean up session ${test["Session"]}: ${deleteRes.status}, ${deleteRes.body}`);
    }
  }
}
