"""
AWS utilities for interacting with Bedrock (Nova and Titan models)
"""
import os
import json
import base64
import boto3
from typing import List, Dict, Any
from botocore.exceptions import ClientError
from PIL import Image
from io import BytesIO


class AWSBedrockClient:
    def __init__(self):
        """Initialize AWS Bedrock client"""
        print("🔧 Initializing AWS Bedrock Client...")
        
        # Get AWS credentials from environment
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize Bedrock Runtime client
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=self.aws_region,
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key
        )
        
        print(f"✅ AWS Bedrock Client initialized (Region: {self.aws_region})\n")
    
    def get_nova_response(self, prompt: str, image_base64: str = None, 
                         model_id: str = "us.amazon.nova-lite-v1:0") -> Dict[str, Any]:
        """
        Get response from Amazon Nova model
        Can handle both text-only and multimodal (text + image) requests
        """
        print(f"🤖 Calling Amazon Nova model: {model_id}...")
        
        try:
            # Prepare the request body
            if image_base64:
                # Convert image to PNG if needed (Nova requires PNG)
                from PIL import Image
                import io
                
                try:
                    # Decode base64 image
                    image_bytes = base64.b64decode(image_base64)
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Convert to PNG
                    png_buffer = io.BytesIO()
                    image.convert('RGB').save(png_buffer, format='PNG')
                    png_bytes = png_buffer.getvalue()
                    png_base64 = base64.b64encode(png_bytes).decode('utf-8')
                    
                except Exception as e:
                    print(f"⚠️ Image conversion warning: {e}")
                    png_base64 = image_base64  # Use original if conversion fails
                
                # Multimodal request (text + image)
                body = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "image": {
                                        "format": "png",
                                        "source": {
                                            "bytes": png_base64
                                        }
                                    }
                                },
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "inferenceConfig": {
                        "max_new_tokens": 2048,
                        "temperature": 0.3
                    }
                }
            else:
                # Text-only request
                body = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "inferenceConfig": {
                        "max_new_tokens": 2048,
                        "temperature": 0.3
                    }
                }
            
            # Call the model
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract the text content
            if 'output' in response_body and 'message' in response_body['output']:
                content = response_body['output']['message']['content']
                if isinstance(content, list) and len(content) > 0:
                    text_response = content[0].get('text', '')
                else:
                    text_response = str(content)
            else:
                text_response = str(response_body)
            
            print(f"✅ Nova response received (length: {len(text_response)} chars)\n")
            
            return {
                'success': True,
                'response': text_response,
                'raw_response': response_body
            }
            
        except ClientError as e:
            error_msg = f"AWS Bedrock error: {str(e)}"
            print(f"❌ {error_msg}\n")
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Error calling Nova: {str(e)}"
            print(f"❌ {error_msg}\n")
            return {
                'success': False,
                'error': error_msg
            }
    
    def analyze_table(self, table_text: str) -> Dict[str, Any]:
        """
        Analyze a table and get SQL CREATE TABLE and INSERT statements from Nova
        """
        prompt = f"""You are a SQL expert. Analyze the following table data and generate SQL statements to create and populate the table.
        
Table Data:
{table_text}

Instructions:
1. Infer appropriate column names and data types from the table
2. Create a valid PostgreSQL CREATE TABLE IF NOT EXISTS statement
3. Use appropriate data types (TEXT, INTEGER, FLOAT, DATE, etc.)
4. Generate a meaningful table name based on the content
5. IMPORTANT: Use CREATE TABLE IF NOT EXISTS to avoid errors if table exists
6. Generate INSERT statements to populate the table with ALL the data shown in the table
7. Return the SQL CREATE TABLE statement followed by INSERT statements, nothing else

SQL Statement:"""
        
        print("📋 Analyzing table structure with Nova...")
        result = self.get_nova_response(prompt)
        
        if result['success']:
            sql_query = result['response'].strip()
            # Clean up the SQL query
            if '```sql' in sql_query:
                sql_query = sql_query.split('```sql')[1].split('```')[0].strip()
            elif '```' in sql_query:
                sql_query = sql_query.split('```')[1].split('```')[0].strip()
            
            print(f"✅ Generated SQL CREATE TABLE and INSERT statements\n")
            return {
                'success': True,
                'sql_query': sql_query
            }
        else:
            return result
    
    def analyze_image(self, image_base64: str, image_type: str = "general") -> Dict[str, Any]:
        """
        Analyze an image with Nova
        - For general images: get a summary
        - For data visualization: get SQL to recreate the underlying table
        """
        if image_type == "visualization":
            prompt = """You are analyzing a data visualization (chart, graph, or plot). 
            
Your task:
1. Identify the type of visualization (bar chart, line chart, pie chart, scatter plot, etc.)
2. Extract all data points visible in the visualization
3. Generate a PostgreSQL CREATE TABLE IF NOT EXISTS statement that would store the data used to create this visualization
4. The table should include all columns needed to recreate this exact visualization
5. IMPORTANT: Use CREATE TABLE IF NOT EXISTS to avoid errors if table already exists

Return ONLY the SQL CREATE TABLE IF NOT EXISTS statement with INSERT statements for the data points you can extract, nothing else.

SQL Statement:"""
        else:
            prompt = """You are analyzing an image. Provide a detailed but concise summary of what you see in this image.
            
Focus on:
1. Main subjects or objects
2. Key details and context
3. Any text visible in the image
4. The overall purpose or meaning

Summary:"""
        
        print(f"🖼️ Analyzing image as {image_type}...")
        result = self.get_nova_response(prompt, image_base64=image_base64)
        
        if result['success']:
            response_text = result['response'].strip()
            
            if image_type == "visualization":
                # Extract SQL query
                sql_query = response_text
                if '```sql' in sql_query:
                    sql_query = sql_query.split('```sql')[1].split('```')[0].strip()
                elif '```' in sql_query:
                    sql_query = sql_query.split('```')[1].split('```')[0].strip()
                
                print(f"✅ Generated SQL for visualization data\n")
                return {
                    'success': True,
                    'sql_query': sql_query,
                    'is_visualization': True
                }
            else:
                print(f"✅ Generated image summary\n")
                return {
                    'success': True,
                    'summary': response_text,
                    'is_visualization': False
                }
        else:
            return result
    
    def get_titan_embeddings(self, text: str, model_id: str = "amazon.titan-embed-text-v2:0") -> Dict[str, Any]:
        """
        Get embeddings from Amazon Titan model
        """
        try:
            # Prepare request for Titan
            body = json.dumps({
                "inputText": text
            })
            
            # Call Titan embedding model
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding', [])
            
            return {
                'success': True,
                'embedding': embedding,
                'dimension': len(embedding)
            }
            
        except Exception as e:
            error_msg = f"Error getting Titan embeddings: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    def get_titan_multimodal_embeddings(self, text: str = None, image_base64: str = None,
                                       model_id: str = "amazon.titan-embed-image-v1") -> Dict[str, Any]:
        """
        Get multimodal embeddings from Amazon Titan
        """
        try:
            body_content = {}
            
            if text:
                body_content["inputText"] = text
            if image_base64:
                body_content["inputImage"] = image_base64
            
            body = json.dumps(body_content)
            
            # Call Titan multimodal embedding model
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=body
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            embedding = response_body.get('embedding', [])
            
            return {
                'success': True,
                'embedding': embedding,
                'dimension': len(embedding)
            }
            
        except Exception as e:
            error_msg = f"Error getting Titan multimodal embeddings: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
