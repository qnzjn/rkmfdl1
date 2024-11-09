from google.cloud import aiplatform
import json

class ChatModeration:
    def __init__(self, api_key):
        self.api_key = api_key
        aiplatform.init(project=api_key)
        
    async def check_message(self, text):
        try:
            # Gemini API를 사용한 텍스트 분석
            prompt = f"""
            다음 텍스트를 분석하여 JSON 형식으로 결과를 반환하세요:
            텍스트: {text}
            
            분석 항목:
            1. is_harmful: 유해성 여부 (boolean)
            2. toxicity_score: 유해도 점수 (0-1)
            3. categories: 감지된 문제 카테고리 (array)
            4. filtered_text: 필터링된 텍스트
            """
            
            response = aiplatform.predict(
                endpoint="text-bison@001",
                instances=[{"prompt": prompt}]
            )
            
            return json.loads(response.predictions[0])
        except Exception as e:
            print(f"Moderation error: {e}")
            return {
                "is_harmful": False,
                "toxicity_score": 0,
                "categories": [],
                "filtered_text": text
            }