import os
import base64
import json
import shutil
from pdf2image import convert_from_path
from openai import OpenAI
import instructor
import datetime
import tempfile
import pandas as pd
from docx import Document
from logger import ActivityLogger
import document_class as document_class  # Assuming this contains your Invoice model


class DocumentParser:
    def __init__(self, output_folder, api_key, user="system"):
        self.user = user
        self.output_folder = output_folder
        self.api_key = api_key
        self.activity_logger = ActivityLogger(agent_name="parser")
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

    def extract_images(self,input_file,temp_dir):
        image_paths = []
        if input_file.lower().endswith('.pdf'):

            images = convert_from_path(input_file)

            for i, image in enumerate(images):
                image_path = os.path.join(temp_dir, f'image_page_{i+1}.jpg')
                image.save(image_path, 'JPEG')
                image_paths.append(image_path)
        elif input_file.lower().endswith(('.jpg', '.jpeg', '.png')):
            destination_path = os.path.join(temp_dir, os.path.basename(input_file))
            shutil.copy(input_file, destination_path)
            image_paths.append(destination_path)
        else:
            raise ValueError("Unsupported file format. Please provide a PDF or image file.")

        return image_paths

    def extract_text(self, input_file):
        if input_file.lower().endswith('.docx'):
            doc = Document(input_file)
            return '\n'.join([p.text for p in doc.paragraphs])
        elif input_file.lower().endswith(('.xlsx', '.xls')):
            dfs = pd.read_excel(input_file, sheet_name=None)
            return '\n'.join([df.to_string(index=False) for df in dfs.values()])
        elif input_file.lower().endswith('.pdf'):
            return None  # Image-based, handled separately
        else:
            raise ValueError("Unsupported file format for text extraction.")

    def encode_images(self,image_paths):
        encoded_images = []
        for image_path in image_paths:
            with open(image_path, "rb") as img_file:
                encoded_image = base64.b64encode(img_file.read()).decode('utf-8')
                encoded_images.append(encoded_image)
        
        return encoded_images

    def prepare_messages(self, encoded_images=None, text_input=None):
        messages = [{
            "role": "user",
            "content": "Your goal is to extract structured information from the provided document."
        }]

        if text_input:
            messages.append({
                "role": "user",
                "content": text_input
            })
        elif encoded_images:
            for encoded_image in encoded_images:
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded_image}"
                        }
                    }]
                })
        else:
            raise ValueError("No input provided for message preparation.")

        print(f"-------------------------messages for LLM")
        print(messages)
        print(f"=" * 50)
        return messages

    def generate_response(self, messages, doctype):
        print("Generating response...")
        if doctype == 'PO':
            model = document_class.PO
            field = 'po_number'
        elif doctype == 'Invoice':
            model = document_class.Invoice
            field = 'invoice_number'
        elif doctype == 'Contract':
            model = document_class.Contract
            field = 'contract_number'
        else:
            raise ValueError("Unsupported document type. Use 'PO', 'Invoice', or 'Contract'.")

        response = instructor.from_openai(OpenAI(api_key=self.api_key)).chat.completions.create(
            model='gpt-4o',
            response_model=model,
            messages=messages
        )
        print("--------------------------------Response generated.")
        print(response)
        print(f"="*50)

        file_num = response.model_dump()[field]
        return response, file_num

    def save_output(self, response, input_file, doctype):
        def default_serializer(obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        target_dir = os.path.join(self.output_folder, doctype)
        os.makedirs(target_dir, exist_ok=True)
        output_filename = os.path.splitext(os.path.basename(input_file))[0] + ".json"
        output_path = os.path.join(target_dir, output_filename)
        with open(output_path, 'w') as file:
            json.dump(response.model_dump(), file, indent=2, default=default_serializer)
        print(f"Output saved to {output_path}")
        return output_filename,output_path

    def process_document(self, input_file, doctype):
        log_dict = {
                "user_id": self.user,
                "input_filename": input_file,
            }
        try:
            if not os.path.exists(input_file):
                log_dict["status"] = "Error"
                log_dict["event_dts"] = datetime.datetime.now()
                log_dict["comments"] = f"File not found: {input_file}"
                self.activity_logger.insert_log(log_dict)
                raise FileNotFoundError(f"The file {input_file} does not exist.")

            ext = os.path.splitext(input_file)[1].lower()

            if ext in ['.jpg', '.jpeg', '.png', '.pdf']:
                # Handle image-based documents
                with tempfile.TemporaryDirectory() as temp_dir:
                    image_paths = self.extract_images(input_file,temp_dir)
                    encoded_images = self.encode_images(image_paths)
                    messages = self.prepare_messages(encoded_images=encoded_images)
            elif ext in ['.docx', '.xlsx', '.xls']:
                # Handle text-based documents
                text_input = self.extract_text(input_file)
                messages = self.prepare_messages(text_input=text_input)
            else:
                log_dict["status"] = "Error"
                log_dict["event_dts"] = datetime.datetime.now()
                log_dict["comments"] = f"Unsupported file type: {ext}"
                self.activity_logger.insert_log(log_dict)
                raise ValueError("Unsupported file type for processing.")

            response, file_num = self.generate_response(messages, doctype)
            output_filename,output_path = self.save_output(response, input_file, doctype)
            log_dict["status"] = "Success"
            log_dict["output_filename"] = output_filename
            log_dict["output_file_location"] = output_path
            log_dict["event_dts"] = datetime.datetime.now()
            log_dict["comments"] = f"Document {input_file} processed successfully: {output_filename} stored at {output_path}"
            self.activity_logger.insert_log(log_dict)
            return output_filename, file_num
        except Exception as e:
            log_dict["status"] = "Error"
            log_dict["event_dts"] = datetime.datetime.now()
            log_dict["comments"] = f"Error processing document {input_file}: {str(e)}"
            self.activity_logger.insert_log(log_dict)


# Example usage
if __name__ == "__main__":
    parser = DocumentParser(
        api_key='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',
        output_folder='G:\INTERNSHIP\Bimbasree_nda\invoice_comparision\storage\parsed',
    )
    parser.process_document(
        input_file="G:\INTERNSHIP\Bimbasree_nda\invoice_comparision\storage\download\PO\Sample_Purchase_Order.pdf",
        doctype='PO'
    )
    parser.activity_logger.fetch_logs_from_table()
