import pdfkit
import asyncio
from concurrent.futures import ThreadPoolExecutor

problem_numbers = [
  2580,
  14499,
  13460,
]

options = {
    'page-size': 'A4',
    'margin-top': '0.75in',
    'margin-right': '0.75in',
    'margin-bottom': '0.75in',
    'margin-left': '0.75in',
}

def download_pdf(link, filename):
  pdfkit.from_url(link, filename, options=options)
  

async def main():
  problem_links = [[num, f"https://www.acmicpc.net/problem/{num}"] for num in problem_numbers]
  
  loop = asyncio.get_event_loop()
  with ThreadPoolExecutor() as executor:
    tasks = [
      loop.run_in_executor(executor, download_pdf, problem_link, f"./outputs/{problem_number}.pdf")
      for problem_number, problem_link in problem_links
    ]
  await asyncio.gather(*tasks)

asyncio.run(main())
