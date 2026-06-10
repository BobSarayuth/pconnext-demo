import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';
import { parseHTML } from 'k6/html'; // Import HTML parsing module

// Custom metrics
const responseTime = new Trend('response_time');
const successRate = new Rate('success_rate');

export const options = {
  vus: 9,           // 9 virtual users
  duration: '30m',   // run for 10 minutes
  thresholds: {
    http_req_duration: ['p(95)<3000'], // 95% of requests should be below 3s
    success_rate: ['rate>0.95'],       // 95% success rate
  },
};

export default function() {
  const startTime = new Date().getTime();
  const res = http.get('http://localhost:8080/');
  const endTime = new Date().getTime();

  // Record response time
  responseTime.add(endTime - startTime);

  // Check if response is valid
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response has valid format': (r) => r.body !== null,
    'response contains expected content': (r) => r.body.includes('<!DOCTYPE html>'),
  });

  successRate.add(success);

  if (success) {
    // Parse HTML to find all resources (e.g., CSS, JS, images)
    const doc = parseHTML(res.body);
    const resources = doc.find('link[rel="stylesheet"]').toArray().map((el) => el.attr('href'))
      .concat(doc.find('script[src]').toArray().map((el) => el.attr('src')))
      .concat(doc.find('img[src]').toArray().map((el) => el.attr('src')));

    // Fetch all resources
    resources.forEach((resource) => {
      if (resource) {
        const resourceRes = http.get(resource.startsWith('http') ? resource : `http://localhost:8080${resource}`);
        check(resourceRes, {
          [`resource ${resource} loaded`]: (r) => r.status === 200,
        });
      }
    });
  }

  // Log details for debugging
  if (!success) {
    console.log(`Failed request: ${res.status}, ${res.body}`);
  }

  // Add random sleep between 1-3 seconds to simulate realistic user behavior
  sleep(Math.random() * 2 + 1);
}
