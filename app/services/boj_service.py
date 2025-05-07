import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import requests
from weasyprint import HTML, CSS
from PyPDF2 import PdfMerger
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BojService:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        # 폰트 파일 경로 설정
        self.font_path = os.path.abspath('./fonts')
        # 출력 디렉토리 생성
        os.makedirs('./outputs', exist_ok=True)
        os.makedirs('./outputs/temp', exist_ok=True)

    def download_and_clean_html(self, problem_number):
        """문제 HTML 다운로드 및 정리"""
        link = f"https://www.acmicpc.net/problem/{problem_number}"

        try:
            response = requests.get(link, headers=self.headers)
            if response.status_code == 403:
                logger.error(f"Access forbidden for {link}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # 특정 클래스명을 가진 요소 제거
            for element in soup.find_all(class_='footer'):
                element.decompose()

            for header in soup.find_all(class_='header'):
                header.decompose()

            for element in soup.find_all(class_='page-header'):
                element['style'] = 'margin: 0;'

            for element in soup.find_all(id='problem_association'):
                element.decompose()

            # 폰트 설정을 위한 스타일 추가
            style_tag = soup.new_tag('style')
            style_tag.string = f'''
              @font-face {{
                font-family: 'Noto Sans';
                src: url('file://{self.font_path}/NotoSans-Regular.ttf') format('truetype');
              }}
              body {{
                font-family: 'Noto Sans', sans-serif;
                max-width: 100%;
              }}
              container {{
                width: 100%;
              }}
              pre, code, kbd, samp {{
                font-family: 'Noto Sans', monospace;
              }}
            '''
            soup.head.append(style_tag)

            return str(soup)
        except Exception as e:
            logger.error(f"Error downloading problem {problem_number}: {str(e)}")
            return None

    async def save_html_to_file(self, html, output_path):
        """HTML을 파일로 저장"""
        temp_html_path = output_path.replace('.pdf', '.html')
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_file, temp_html_path, html)
        logger.info(f"Saved cleaned HTML to {temp_html_path}")
        return temp_html_path

    def _write_file(self, temp_html_path, html):
        """파일 작성 헬퍼 함수"""
        with open(temp_html_path, 'w', encoding='utf-8') as file:
            file.write(html)

    def convert_html_to_pdf(self, temp_html_path, output_path):
        """HTML을 PDF로 변환"""
        try:
            css = CSS(string=f'''
              @font-face {{
                font-family: 'Noto Sans';
                src: url('file://{self.font_path}/NotoSans-Regular.ttf') format('truetype');
              }}
              body {{
                font-family: 'Noto Sans', sans-serif;
                max-width: 100%;
              }}
              container {{
                width: 100%;
              }}
              h1, h2, h3, h4, h5, p, div, span, text, pre, code, kbd, samp {{
                font-family: 'Noto Sans', monospace;
              }}
            ''')
            # HTML을 PDF로 변환
            HTML(temp_html_path).write_pdf(output_path, stylesheets=[css])
            # 임시 HTML 파일 삭제
            os.remove(temp_html_path)
            logger.info(f"Converted HTML to PDF: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error converting HTML to PDF: {str(e)}")
            return False

    async def process_problem(self, problem_number, temp_dir):
        """단일 문제 처리"""
        output_pdf_path = f"{temp_dir}/{problem_number}.pdf"

        html = self.download_and_clean_html(problem_number)
        if html is None:
            return None

        temp_html_path = await self.save_html_to_file(html, output_pdf_path)
        success = await asyncio.get_running_loop().run_in_executor(
            None, self.convert_html_to_pdf, temp_html_path, output_pdf_path
        )

        if success:
            return output_pdf_path
        return None

    async def generate_pdf(self, problems, output_path):
        """여러 문제 세트를 PDF로 변환"""
        temp_dir = "./outputs/temp"
        os.makedirs(temp_dir, exist_ok=True)

        # 각 문제 처리
        tasks = [self.process_problem(problem_number, temp_dir) for problem_number in problems]
        results = await asyncio.gather(*tasks)

        # 성공적으로 생성된 PDF 파일 필터링
        all_pdfs = [pdf_path for pdf_path in results if pdf_path is not None]

        # PDF 병합
        if all_pdfs:
            merger = PdfMerger()
            for pdf_path in all_pdfs:
                if os.path.exists(pdf_path):
                    merger.append(pdf_path)

            merger.write(output_path)
            merger.close()

            # 임시 PDF 파일 삭제
            for pdf_path in all_pdfs:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

            logger.info(f"Created merged PDF: {output_path}")
            return output_path
        else:
            raise Exception("No PDF files were generated")
