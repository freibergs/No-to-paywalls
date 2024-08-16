from flask import Flask, request, render_template, redirect, url_for, flash
import requests
from bs4 import BeautifulSoup
from db_utils import init_db, get_article_from_cache, save_article_to_cache
import re
from dotenv import load_dotenv
import os

load_dotenv()

delfi_token = os.getenv('DELFI_TOKEN')
delfi_hash = os.getenv('DELFI_HASH')
tvnet_cookie = os.getenv('TVNET_COOKIE')
agent = os.getenv('USER_AGENT')
error_msg = os.getenv('ERROR_MSG')
info_text = os.getenv('INFO_TEXT')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

def extract_tvnet_id(url):
    match = re.search(r'tvnet.lv/(\d+)', url)
    if match:
        return match.group(1)
    return None

def get_tvnet_article(article_id, full_url=None):
    cached_article = get_article_from_cache(article_id)
    if cached_article:
        return cached_article

    if full_url:
        try:
            headers = {
                "Cookie": tvnet_cookie,
                "User-Agent": agent,
            }
            response = requests.get(full_url, headers=headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            title = soup.find('h1', class_='article-superheader__headline').get_text(strip=True)
            title = re.sub(r'\(\d+\)$', '', title).strip()
            
            lead = soup.find('div', class_='article-body__item article-body__item--htmlElement article-body__item--lead').get_text(strip=True)
            
            image_div = soup.find('div', class_='article-superheader__background')
            if image_div and 'style' in image_div.attrs:
                style = image_div['style']
                start = style.find("url('") + len("url('")
                end = style.find("')", start)
                image_url = "https:" + style[start:end]
            else:
                image_url = None
            
            article_items = soup.find_all(class_=[
                'article-body__item article-body__item--htmlElement',
                'article-body__item article-body__item--highlightedContent'
            ])
            
            content = ''
            for item in article_items:
                for child in item.children:
                    if child.name:
                        content += str(child)
            
            content_soup = BeautifulSoup(content, 'html.parser')
            
            for a_tag in content_soup.find_all('a'):
                a_tag.unwrap()
            
            for p_tag in content_soup.find_all('p'):
                p_tag['class'] = p_tag.get('class', []) + ['mb-4', 'text-lg', 'leading-relaxed']
            
            for ul_tag in content_soup.find_all('ul'):
                ul_tag['class'] = ul_tag.get('class', []) + ['list-disc', 'pl-5', 'mb-4']
            
            for li_tag in content_soup.find_all('li'):
                li_tag['class'] = li_tag.get('class', []) + ['mb-2']
            
            content = str(content_soup)
            
            save_article_to_cache(article_id, title, lead, content, image_url, full_url, source='tvnet')
           
            return {"title": title, "lead": lead, "text_content": content, "meta_image_url": image_url, "full_url": full_url}
       
        except (requests.RequestException, KeyError, IndexError) as e:
            return None
    else:
        return None


def get_delfi_article(article_id):
    cached_article = get_article_from_cache(article_id)
    if cached_article:
        return cached_article
    
    try:
        url = f"https://content.api.delfi.lv/content/v3/graphql?operationName=getArticleByID&variables=%7B%22id%22:{article_id}%7D&extensions=%7B%22persistedQuery%22:%7B%22version%22:1,%22sha256Hash%22:%{delfi_hash}%22%7D%7D"
        
        headers = {
            "Authorization": f"Bearer {delfi_token}",
            "User-Agent": agent,
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        data = response.json()
        title = data['data']['article']['data'][0]['content']['title']['text']
        lead = data['data']['article']['data'][0]['content']['lead']['text']
        text_content = data['data']['article']['data'][0]['content']['body']['text']
        full_url = "https://" + data['data']['article']['data'][0]['url']

        paragraphs = text_content.split('\n')
        processed_content = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph:
                word_count = len(paragraph.split())
                if word_count < 10:
                    processed_content += f'<h3 class="text-2xl font-semibold mb-4">{paragraph}</h3>'
                else:
                    processed_content += f'<p class="mb-4 text-lg leading-relaxed">{paragraph}</p>'

        meta_image_id = data['data']['article']['data'][0]['metaImage']['id']
        meta_image_url = f'https://images.delfi.lv/media-api-image-cropper/v1/{meta_image_id}.jpg?w=720'
        
        save_article_to_cache(article_id, title, lead, processed_content, meta_image_url, full_url, source='delfi')
        
        return {"title": title, "lead": lead, "text_content": processed_content, "meta_image_url": meta_image_url, "full_url": full_url}
    
    except (requests.RequestException, KeyError, IndexError) as e:
        flash(error_msg, 'error')
        return None

@app.route('/delfi/<id>')
def delfi_article(id):
    article_data = get_delfi_article(id)
    if article_data:
        return render_template('article.html', **article_data)
    else:
        return redirect(url_for('index'))

@app.route('/tvnet/<id>')
def tvnet_article(id):
    article_data = get_article_from_cache(id)
    if not article_data:
        article_data = get_tvnet_article(id)
    if article_data:
        return render_template('article.html', **article_data)
    else:
        flash(error_msg, 'error')
        return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        
        if "tvnet.lv" in url:
            article_id = extract_tvnet_id(url)
            if not article_id:
                flash(error_msg, 'error')
                return redirect(url_for('index'))

            get_tvnet_article(article_id, full_url=url)
            return redirect(url_for('tvnet_article', id=article_id))
        
        elif "delfi.lv" in url:
            match = re.findall(r'/(\d+)/', url)
            if not match:
                flash(error_msg, 'error')
                return redirect(url_for('index'))

            article_id = match[-1]
            return redirect(url_for('delfi_article', id=article_id))
        
        else:
            flash(error_msg, 'error')
            return redirect(url_for('index'))

    return render_template('index.html', info_text=info_text)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0')