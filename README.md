# `Foodgram` - сайт 'Продуктовый помощник'

#### О проекте:
 Онлайн-сервис и API для него. На этом сервисе пользователи могут публиковать рецепты, подписываться на публикации других пользователей, добавлять понравившиеся рецепты в список «Избранное», а перед походом в магазин скачивать сводный список продуктов, необходимых для приготовления одного или нескольких выбранных блюд.
 
#### Технологии:
- Python
- Django
- Django REST Framework
- PostgreSQL
- Nginx
- Gunicorn
- Docker

#### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

'https://github.com/LianaGataullina/foodgram-project-react.git'

`cd foodgram-project-react`

Установить Docker и Docker Compose

`sudo apt install docker-ce docker-compose -y`

Запуск контейнера:

`docker-compose up -d`

Заполнение базы данными:

`sudo docker-compose exec backend python manage.py collectstatic --no-input`

`sudo docker-compose exec backend python manage.py makemigrations --noinput`

`sudo docker-compose exec backend python manage.py migrate --noinput`

`sudo docker-compose exec backend python manage.py createsuperuser`

`sudo docker-compose exec backend python manage.py loader`


Суперпользователь:

`Адрес электронной почты: test@yandex.ru`

`Пароль: test`
