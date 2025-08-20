// Test connectivity to Cloud Run service from different environments
const https = require('https');

const BACKEND_URL = 'https://copernicus-podcast-api-204731194849.us-central1.run.app';

async function testHealth() {
  console.log('🔍 Testing health endpoint...');
  try {
    const response = await fetch(`${BACKEND_URL}/health`);
    const data = await response.json();
    console.log('✅ Health check successful:', data);
    return true;
  } catch (error) {
    console.error('❌ Health check failed:', error.message);
    return false;
  }
}

async function testAPI() {
  console.log('🔍 Testing API endpoint...');
  try {
    const response = await fetch(`${BACKEND_URL}/generate-legacy-podcast`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'Connectivity-Test/1.0',
      },
      body: JSON.stringify({
        subject: 'Connectivity Test',
        duration: '5 minutes',
        speakers: '2',
        difficulty: 'intermediate',
        timestamp: Date.now()
      })
    });
    
    const data = await response.json();
    console.log('✅ API test successful:', data);
    return true;
  } catch (error) {
    console.error('❌ API test failed:', error.message);
    return false;
  }
}

async function runTests() {
  console.log('🚀 Starting connectivity tests...');
  console.log(`📍 Target: ${BACKEND_URL}`);
  console.log(`📍 Environment: Node.js ${process.version}`);
  console.log(`📍 Timestamp: ${new Date().toISOString()}`);
  console.log('');
  
  const healthOk = await testHealth();
  console.log('');
  
  if (healthOk) {
    await testAPI();
  }
  
  console.log('');
  console.log('🏁 Tests completed');
}

runTests().catch(console.error);
