# 📢 Marketing API — Управление маркетинговыми кампаниями

## Описание

Модуль для управления маркетинговыми кампаниями в различных каналах: Instagram, Facebook, Google Ads, и т.д.

## Основные сущности

### Campaign (Кампания)
Рекламная кампания в определённом канале на определённый период.

**Параметры:**
- Название кампании
- Платформа (Instagram, Facebook, Google)
- Бюджет
- Период (дата начала и окончания)
- Статус (активна, на паузе, завершена)
- Метрики (показы, клики, конверсии)

## Эндпоинты

### Список кампаний

#### `GET /campaigns/`
Получить список всех кампаний с фильтрацией.

**Query параметры:**
- `skip` — пропустить N записей (по умолчанию 0)
- `limit` — максимум записей (1-1000, по умолчанию 100)
- `platform` — фильтр по платформе (Instagram, Facebook, Google, TikTok)
- `status` — фильтр по статусу (ACTIVE, PAUSED, COMPLETED)

**Response:**
```json
[
  {
    "id": 1,
    "name": "Запуск ЖК Рассвет",
    "platform": "Instagram",
    "status": "ACTIVE",
    "budget": 50000,
    "spent": 12500,
    "start_date": "2025-12-01",
    "end_date": "2025-12-31",
    "impressions": 125000,
    "clicks": 3500,
    "conversions": 87,
    "created_at": "2025-11-25T10:00:00Z"
  },
  ...
]
```

### Детали кампании

#### `GET /campaigns/{campaign_id}`
Получить детальную информацию о кампании.

**Response:**
```json
{
  "id": 1,
  "name": "Запуск ЖК Рассвет",
  "description": "Продвижение нового ЖК через Instagram Stories и Feed",
  "platform": "Instagram",
  "status": "ACTIVE",
  "budget": 50000,
  "spent": 12500,
  "remaining": 37500,
  "start_date": "2025-12-01",
  "end_date": "2025-12-31",
  "target_audience": {
    "age": "25-45",
    "location": "Ташкент",
    "interests": ["недвижимость", "инвестиции"]
  },
  "metrics": {
    "impressions": 125000,
    "clicks": 3500,
    "ctr": 2.8,
    "conversions": 87,
    "cpa": 143.68,
    "roi": 3.2
  },
  "created_by": {
    "id": 3,
    "name": "Маркетолог Петров"
  }
}
```

### Создание кампании

#### `POST /campaigns/`
Создать новую маркетинговую кампанию.

**Request:**
```json
{
  "name": "Новогодняя акция",
  "description": "Скидки до 15% на квартиры",
  "platform": "Instagram",
  "budget": 30000,
  "start_date": "2025-12-20",
  "end_date": "2026-01-10",
  "target_audience": {
    "age": "25-45",
    "location": "Ташкент",
    "interests": ["недвижимость"]
  }
}
```

**Response:** (статус 201 Created)
```json
{
  "id": 15,
  "name": "Новогодняя акция",
  "status": "ACTIVE",
  "created_at": "2025-12-03T10:00:00Z"
}
```

### Обновление кампании

#### `PUT /campaigns/{campaign_id}`
Обновить данные кампании.

**Request:**
```json
{
  "status": "PAUSED",
  "budget": 40000,
  "description": "Расширенная новогодняя акция"
}
```

### Удаление кампании

#### `DELETE /campaigns/{campaign_id}`
Удалить кампанию (только для админов).

**Response:** 204 No Content

### Статистика кампании

#### `GET /campaigns/{campaign_id}/stats`
Получить детальную статистику по кампании.

**Response:**
```json
{
  "campaign_id": 1,
  "period": {
    "start": "2025-12-01",
    "end": "2025-12-31",
    "days_elapsed": 3,
    "days_remaining": 28
  },
  "budget": {
    "total": 50000,
    "spent": 12500,
    "remaining": 37500,
    "daily_avg": 4166.67,
    "daily_spent": 4166.67
  },
  "performance": {
    "impressions": 125000,
    "clicks": 3500,
    "ctr": 2.8,
    "conversions": 87,
    "conversion_rate": 2.49,
    "cpc": 3.57,
    "cpa": 143.68
  },
  "roi": {
    "revenue": 4350000,
    "cost": 12500,
    "profit": 4337500,
    "roi_percent": 34700
  },
  "daily_breakdown": [
    {
      "date": "2025-12-01",
      "impressions": 45000,
      "clicks": 1200,
      "conversions": 28,
      "spent": 4200
    },
    ...
  ]
}
```

### Поиск кампаний

#### `GET /campaigns/search`
Поиск кампаний по названию или аккаунту.

**Query параметры:**
- `query` — строка поиска (минимум 1 символ)
- `skip` — пропустить N записей (по умолчанию 0)
- `limit` — максимум результатов (1-100, по умолчанию 10)

**Пример:**
```
GET /campaigns/search?query=Рассвет&limit=20
```

## Модели БД

### Campaign
```python
- id: int (PK)
- name: str                    # Название кампании
- description: str (optional)  # Описание
- platform: str               # Instagram, Facebook, Google, TikTok
- status: str                 # ACTIVE, PAUSED, COMPLETED
- budget: float               # Бюджет в $
- spent: float                # Потрачено в $
- start_date: date            # Дата начала
- end_date: date              # Дата окончания
- target_audience: JSON       # Целевая аудитория
- created_by: int (FK -> User)
- created_at: datetime
- updated_at: datetime
```

### CampaignMetrics
```python
- id: int (PK)
- campaign_id: int (FK -> Campaign)
- date: date                  # Дата метрики
- impressions: int            # Показы
- clicks: int                 # Клики
- conversions: int            # Конверсии (лиды)
- spent: float                # Потрачено за день
- revenue: float (optional)   # Доход от лидов
```

## CRUD функции

Расположение: `backend/database/marketing/crud.py`

### CampaignCRUD

```python
class CampaignCRUD:
    def get_campaigns(db, skip, limit, platform, status):
        """Получить список кампаний с фильтрами"""
        
    def get_campaign(db, campaign_id):
        """Получить кампанию по ID"""
        
    def create_campaign(db, data: CampaignCreate):
        """Создать новую кампанию"""
        
    def update_campaign(db, campaign_id, data: CampaignUpdate):
        """Обновить кампанию"""
        
    def delete_campaign(db, campaign_id):
        """Удалить кампанию"""
        
    def get_statistics(db, campaign_id):
        """Получить статистику кампании"""
        
    def search_campaigns(db, query, skip, limit):
        """Поиск кампаний"""
```

## Платформы

### Instagram
- Stories рекламa
- Feed реклама
- Reels реклама
- Таргетинг по интересам

### Facebook
- Feed реклама
- Видео реклама
- Карусель
- Динамические объявления

### Google Ads
- Поисковая реклама
- Контекстно-медийная сеть
- YouTube реклама
- Ремаркетинг

### TikTok
- In-Feed реклама
- TopView
- Brand Takeover

## Метрики

### Базовые метрики

**Impressions (Показы)**
- Количество раз, когда объявление было показано

**Clicks (Клики)**
- Количество кликов по объявлению

**CTR (Click-Through Rate)**
- Процент кликов от показов
- Формула: `(Clicks / Impressions) * 100`

**Conversions (Конверсии)**
- Количество лидов, полученных с кампании

**Conversion Rate**
- Процент конверсий от кликов
- Формула: `(Conversions / Clicks) * 100`

### Финансовые метрики

**CPC (Cost Per Click)**
- Стоимость одного клика
- Формула: `Spent / Clicks`

**CPA (Cost Per Acquisition)**
- Стоимость привлечения одного лида
- Формула: `Spent / Conversions`

**ROI (Return on Investment)**
- Возврат инвестиций
- Формула: `((Revenue - Spent) / Spent) * 100`

## Примеры использования

### JavaScript: Получение кампаний

```javascript
async function loadCampaigns(platform = null) {
  const params = new URLSearchParams();
  if (platform) params.append('platform', platform);
  params.append('limit', '50');
  
  const response = await fetch(`/campaigns/?${params}`);
  const campaigns = await response.json();
  
  campaigns.forEach(campaign => {
    console.log(`${campaign.name}: ${campaign.clicks} кликов, ${campaign.conversions} лидов`);
  });
}
```

### JavaScript: Создание кампании

```javascript
async function createCampaign(data) {
  const response = await fetch('/campaigns/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      name: data.name,
      platform: data.platform,
      budget: data.budget,
      start_date: data.startDate,
      end_date: data.endDate,
      target_audience: {
        age: "25-45",
        location: "Ташкент",
        interests: ["недвижимость"]
      }
    })
  });
  
  if (response.ok) {
    const campaign = await response.json();
    console.log('Кампания создана:', campaign.id);
  }
}
```

### JavaScript: Статистика

```javascript
async function displayStats(campaignId) {
  const response = await fetch(`/campaigns/${campaignId}/stats`);
  const stats = await response.json();
  
  console.log(`ROI: ${stats.roi.roi_percent}%`);
  console.log(`CPA: $${stats.performance.cpa}`);
  console.log(`Конверсий: ${stats.performance.conversions}`);
  
  // Отобразить график
  renderChart(stats.daily_breakdown);
}
```

## Интеграции

### Instagram Basic Display API
- Получение метрик из Instagram Insights
- Автоматическое обновление статистики

### Facebook Ads API
- Управление кампаниями через API
- Получение данных о показах и кликах

### Google Analytics
- Отслеживание переходов на сайт
- Анализ поведения пользователей

## Автоматизация

### Автоматическое обновление метрик

```python
# В Celery задаче
@celery.task
def update_campaign_metrics():
    campaigns = db.query(Campaign).filter(Campaign.status == "ACTIVE").all()
    
    for campaign in campaigns:
        if campaign.platform == "Instagram":
            metrics = fetch_instagram_metrics(campaign)
        elif campaign.platform == "Facebook":
            metrics = fetch_facebook_metrics(campaign)
        
        CampaignMetrics.create(
            campaign_id=campaign.id,
            date=datetime.now().date(),
            **metrics
        )
```

### Уведомления

- **Низкий ROI:** Если ROI < 100%, уведомить маркетолога
- **Бюджет исчерпан:** Когда `spent >= budget * 0.9`
- **Высокая конверсия:** Если conversion_rate > 5%

## Права доступа

Роль | Создание | Просмотр | Редактирование | Удаление
-----|----------|----------|----------------|----------
Админ | ✅ | Все | Все | ✅
РОП | ✅ | Все | Все | ✅
Маркетинг | ✅ | Все | Свои | Свои
МОП | ❌ | Все | ❌ | ❌
Продажник | ❌ | ❌ | ❌ | ❌

## TODO

- [ ] Интеграция с Facebook Ads API
- [ ] Интеграция с Google Ads API
- [ ] Автоматическое A/B тестирование креативов
- [ ] Предсказание конверсий (ML модель)
- [ ] Дашборд с графиками
- [ ] Экспорт отчётов в PDF/Excel
- [ ] UTM-метки для отслеживания источников

---

**Автор:** RealEstate CRM Team  
**Дата:** 2025

