import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import requests
from weasyprint import HTML, CSS
from PyPDF2 import PdfMerger
from datetime import datetime

class BojToPdf:
    def __init__(self, problem_numbers, set_number):
        self.problem_numbers = problem_numbers
        self.set_number = set_number
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

    def download_and_clean_html(self, link):
        response = requests.get(link, headers=self.headers)
        if response.status_code == 403:
            print(f"Access forbidden for {link}")
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
        path_to_font = os.path.abspath('./fonts')
        style_tag = soup.new_tag('style')
        style_tag.string = f'''
          @font-face {{
            font-family: 'Noto Sans';
            src: url('file://{path_to_font}/NotoSans-Regular.ttf') format('truetype');
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

    def save_html_to_file(self, html, output_path):
        temp_html_path = output_path.replace('.pdf', '.html')
        with open(temp_html_path, 'w', encoding='utf-8') as file:
            file.write(html)
        print(f"Saved cleaned HTML to {temp_html_path}")
        return temp_html_path

    def convert_html_to_pdf(self, temp_html_path, output_path):
        path_to_font = os.path.abspath('./fonts')
        css = CSS(string=f'''
          @font-face {{
            font-family: 'Noto Sans';
            src: url('file://{path_to_font}/NotoSans-Regular.ttf') format('truetype');
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
          table, th, td {{
            max-width: 100%;
          }} 
        ''')
        # HTML을 PDF로 변환
        HTML(temp_html_path).write_pdf(output_path, stylesheets=[css])
        # 임시 HTML 파일 삭제
        os.remove(temp_html_path)

    async def process_problems(self):
        os.makedirs('./outputs', exist_ok=True)

        problem_links = [[num, f"https://www.acmicpc.net/problem/{num}"] for num in self.problem_numbers]
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            # HTML 다운로드 및 정리 작업
            html_tasks = [
                loop.run_in_executor(executor, self.download_and_clean_html, problem_link)
                for problem_number, problem_link in problem_links
            ]
            html_contents = await asyncio.gather(*html_tasks)
            
            # HTML 저장 작업
            save_tasks = []
            temp_html_paths = []
            for problem_number, html in zip(self.problem_numbers, html_contents):
                if html is not None:
                    output_pdf_path = f"./outputs/{problem_number}.pdf"
                    temp_html_path = self.save_html_to_file(html, output_pdf_path)
                    temp_html_paths.append((temp_html_path, output_pdf_path))
            
            # PDF 변환 작업
            pdf_tasks = [
                loop.run_in_executor(executor, self.convert_html_to_pdf, temp_html_path, output_pdf_path)
                for temp_html_path, output_pdf_path in temp_html_paths
            ]
            await asyncio.gather(*pdf_tasks)

            # PDF 병합
            merger = PdfMerger()
            for problem_number in self.problem_numbers:
                pdf_path = f"./outputs/{problem_number}.pdf"
                if os.path.exists(pdf_path):
                    merger.append(pdf_path)
            
            # 오늘 날짜로 된 파일 이름 생성
            today_str = datetime.today().strftime('%Y-%m-%d')
            merged_pdf_path = f"./outputs/{today_str}-문제집-{self.set_number}.pdf"
            merger.write(merged_pdf_path)
            merger.close()

            # 개별 PDF 파일 삭제
            for problem_number in self.problem_numbers:
                pdf_path = f"./outputs/{problem_number}.pdf"
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            print(f"Created merged PDF: {merged_pdf_path}")

async def main():
    problem_sets = [
        # [14499, 13460, 12100, 14891],
        # [17144, 15683, 3055, 14890],
        # [1202, 2589, 9466, 11000],
    ]

    tasks = []
    for set_number, problem_set in enumerate(problem_sets, start=1):
        boj_to_pdf = BojToPdf(problem_set, set_number)
        tasks.append(boj_to_pdf.process_problems())

    await asyncio.gather(*tasks)

asyncio.run(main())
