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
    
    def analyze_table(self, table_text: str, context_before: str = "", context_after: str = "") -> Dict[str, Any]:
        """
        Analyze a table and get SQL CREATE TABLE and INSERT statements from Nova
        
        Args:
            table_text: The markdown table content
            context_before: Text appearing before the table (for context)
            context_after: Text appearing after the table (for context)
        """
        # Build context-aware prompt
        context_section = ""
        if context_before or context_after:
            context_section = "\n\nDocument Context (for naming and understanding):"
            if context_before:
                context_section += f"\n--- Text before table ---\n{context_before[:300]}"
            if context_after:
                context_section += f"\n--- Text after table ---\n{context_after[:300]}"
        
        prompt = f"""You are a PostgreSQL expert. Analyze the following table and generate SQL to create and populate it.
{context_section}

Table Data:
{table_text}

⚠️ CRITICAL INSTRUCTIONS:
1. **Table Name**: Use context above to create a descriptive table name (lowercase, underscore_separated)
2. **Column Names**: Infer from table headers, use lowercase with underscores
3. **Data Types**: Use appropriate PostgreSQL types (TEXT, INTEGER, NUMERIC, DATE, BOOLEAN)
   - Use NUMERIC for all decimal numbers (not FLOAT)
   - Use TEXT for any non-numeric data
   - Use INTEGER only for whole numbers
4. **Missing Data**: Replace any missing/empty cells with 'NA' (as TEXT)
5. **Special Characters**: 
   - Remove or replace special dashes (–, —) with standard hyphen (-)
   - Escape single quotes in text values (')
   - Remove any non-standard Unicode characters
6. **DO NOT USE**: LOAD_FILE(), BLOB types, or any file system functions
7. **Format**: CREATE TABLE IF NOT EXISTS ... followed by INSERT INTO statements
8. **Quotes**: Properly quote all TEXT values in INSERT statements

Generate ONLY the SQL statements (no explanations):

SQL Statement:"""
        
        print("📋 Analyzing table structure with Nova (with context)...")
        result = self.get_nova_response(prompt, model_id="us.amazon.nova-pro-v1:0")
        
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
    
    def analyze_image(self, image_base64: str, image_type: str = "general", page_context: str = "") -> Dict[str, Any]:
        """
        Analyze an image with Nova
        - For general images: get a summary
        - For data visualization: get SQL to recreate the underlying table
        
        Args:
            image_base64: Base64 encoded image
            image_type: "general" or "visualization"
            page_context: Text context from the page containing the image
        """
        if image_type == "visualization":
            context_section = ""
            if page_context:
                context_section = f"\n\nPage Context (for table naming):\n{page_context[:400]}\n"
            
            prompt = f"""You are analyzing a data visualization (chart, graph, plot).{context_section}

⚠️ CRITICAL INSTRUCTIONS:
1. **Identify**: Type of chart (bar, line, pie, scatter, etc.)
2. **Extract**: All visible data points and labels
3. **Table Name**: Use context above to create descriptive name (lowercase_with_underscores)
4. **Data Types**: 
   - Use NUMERIC for all decimal numbers (NOT FLOAT)
   - Use TEXT for labels and categories
   - Use INTEGER only for whole numbers
5. **Missing Data**: Use 'NA' (as TEXT) for any unclear data points
6. **Special Characters**:
   - Replace special dashes (–, —) with standard hyphen (-)
   - Escape quotes properly
   - Remove non-standard Unicode
7. **DO NOT USE**: LOAD_FILE(), BLOB, file paths, or binary functions
8. **Format**: CREATE TABLE IF NOT EXISTS followed by INSERT statements

Generate ONLY the PostgreSQL SQL (no markdown, no explanations):

SQL Statement:"""
        else:
            prompt = """You are analyzing an image. Provide a detailed but concise summary of what you see.
            
Focus on:
1. Main subjects or objects
2. Key details and context
3. Any text visible in the image
4. The overall purpose or meaning

Summary:"""
        
        print(f"🖼️ Analyzing image as {image_type}...")
        result = self.get_nova_response(prompt, image_base64=image_base64, model_id="us.amazon.nova-pro-v1:0")
        
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
