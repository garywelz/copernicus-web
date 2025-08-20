#!/usr/bin/env python3
"""
API Validation Script for Copernicus AI Secret Manager
Tests all stored API keys for availability and correctness
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from google.cloud import secretmanager
import sys
import os

class APIValidator:
    def __init__(self):
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = "regal-scholar-453620-r7"
        self.results = {}
        
    def get_secret(self, secret_name):
        """Get secret from Google Secret Manager"""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            return None
    
    async def test_google_ai_api(self, api_key):
        """Test Google AI/Gemini API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return {"status": "✅ VALID", "details": "Google AI API accessible"}
                    else:
                        return {"status": "❌ INVALID", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "❌ ERROR", "details": str(e)}
    
    async def test_openai_api(self, api_key):
        """Test OpenAI API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_key}"}
                url = "https://api.openai.com/v1/models"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return {"status": "✅ VALID", "details": "OpenAI API accessible"}
                    else:
                        return {"status": "❌ INVALID", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "❌ ERROR", "details": str(e)}
    
    async def test_elevenlabs_api(self, api_key):
        """Test ElevenLabs API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"xi-api-key": api_key}
                url = "https://api.elevenlabs.io/v1/voices"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return {"status": "✅ VALID", "details": "ElevenLabs API accessible"}
                    else:
                        return {"status": "❌ INVALID", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "❌ ERROR", "details": str(e)}
    
    async def test_nasa_ads_api(self, token):
        """Test NASA ADS API"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {token}"}
                url = "https://api.adsabs.harvard.edu/v1/search/query?q=star&rows=1"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return {"status": "✅ VALID", "details": "NASA ADS API accessible"}
                    else:
                        return {"status": "❌ INVALID", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "❌ ERROR", "details": str(e)}
    
    async def test_pubmed_api(self, api_key):
        """Test PubMed API (NCBI E-utilities)"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=cancer&retmax=1&api_key={api_key}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return {"status": "✅ VALID", "details": "PubMed API accessible"}
                    else:
                        return {"status": "❌ INVALID", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "❌ ERROR", "details": str(e)}
    
    async def test_news_api(self, api_key):
        """Test News API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://newsapi.org/v2/top-headlines?country=us&category=science&apiKey={api_key}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return {"status": "✅ VALID", "details": "News API accessible"}
                    else:
                        return {"status": "❌ INVALID", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "❌ ERROR", "details": str(e)}
    
    async def test_youtube_api(self, api_key):
        """Test YouTube Data API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q=science&type=video&maxResults=1&key={api_key}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return {"status": "✅ VALID", "details": "YouTube API accessible"}
                    else:
                        return {"status": "❌ INVALID", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "❌ ERROR", "details": str(e)}
    
    async def validate_all_apis(self):
        """Validate all APIs in Secret Manager"""
        print("🔍 Validating API Keys from Secret Manager")
        print("=" * 60)
        
        # Test Google AI APIs
        google_ai_key = self.get_secret("GOOGLE_AI_API_KEY")
        if google_ai_key:
            result = await self.test_google_ai_api(google_ai_key)
            print(f"GOOGLE_AI_API_KEY: {result['status']} - {result['details']}")
        
        # Test OpenAI API
        openai_key = self.get_secret("openai-api-key")
        if openai_key:
            result = await self.test_openai_api(openai_key)
            print(f"openai-api-key: {result['status']} - {result['details']}")
        
        # Test ElevenLabs API
        elevenlabs_key = self.get_secret("elevenlabs-api-key")
        if elevenlabs_key:
            result = await self.test_elevenlabs_api(elevenlabs_key)
            print(f"elevenlabs-api-key: {result['status']} - {result['details']}")
        
        # Test NASA ADS API
        nasa_token = self.get_secret("nasa-ads-token")
        if nasa_token:
            result = await self.test_nasa_ads_api(nasa_token)
            print(f"nasa-ads-token: {result['status']} - {result['details']}")
        
        # Test PubMed API
        pubmed_key = self.get_secret("pubmed-api-key")
        if pubmed_key:
            result = await self.test_pubmed_api(pubmed_key)
            print(f"pubmed-api-key: {result['status']} - {result['details']}")
        
        # Test News API
        news_key = self.get_secret("news-api-key")
        if news_key:
            result = await self.test_news_api(news_key)
            print(f"news-api-key: {result['status']} - {result['details']}")
        
        # Test YouTube API
        youtube_key = self.get_secret("youtube-api-key")
        if youtube_key:
            result = await self.test_youtube_api(youtube_key)
            print(f"youtube-api-key: {result['status']} - {result['details']}")
        
        print("\n🎉 API validation completed!")

if __name__ == "__main__":
    validator = APIValidator()
    asyncio.run(validator.validate_all_apis())
