# Caching a Django View

Caching is typically the most effective way to boost an application's performance.

When rendering a template, you'll often have to gather data from various sources and apply some sort of business logic before serving it up to a client. Any delay due to network latency will be noticed by the end user.

For instance, say you have to make an HTTP call to an external API to grab the data required to render a template. Even in perfect conditions this will increase the rending time which will increase the response time. What if the API goes down or maybe you're subject to rate limiting? Either way, if the data is infrequently updated, it's a good idea to implement some sort of caching to prevent having to make the HTTP call altogether for each client request.

This article looks at how to do just that by caching a Django view with Memcached.

*Dependencies:*

1. Django v3.0.5
2. Python v3.8.2
3. Python-memcached v1.59
4. Requests v2.23.0

## Objectives

By the end of this tutorial, you should be able to:

1. Describe Django's built-in options available for caching
1. Configure Django to use Memcached as a Cache Backend
1. Cache a Django view with Memcached

## Django Caching Types

Django comes with several [built-in cache](https://docs.djangoproject.com/en/3.0/topics/cache/) backends, as well as support for a [custom](https://docs.djangoproject.com/en/3.0/topics/cache/#using-a-custom-cache-backend) backend.

The built-in options are:

1. **Memcached** (which we'll use in this article): [Memcached](https://memcached.org/) is a memory-based, key-value store for small chunks of data. It has the ability to share a cache over multiple servers.
1. **Database**: Here the cache fragments are stored in a database. A table for that purpose can be created with one of the Django's admin commands. This isn't the most performant caching type, but it can be useful for storing complex database queries.
1. **File system**: The cache is saved on the file system, in separate files for each cache value. This is the slowest of all the caching types, but it's the easiest to set up in a production environment.
1. **Local memory**: Local memory cache, which is best-suited for development environment. While it's almost as fast as Memcached, it cannot scale beyond a single server.
1. **Dummy**: A "dummy" cache that doesn't actually cache anything but still implements the cache interface. It's meant to be used in development or testing when you don't want caching, but do not wish to change the code.

## Django Caching Levels

Caching in Django can be implemented on different levels (or parts of the site). You can cache the [entire](https://docs.djangoproject.com/en/3.0/topics/cache/#the-per-site-cache) site or specific parts with more granularity:

- [Per-view](https://docs.djangoproject.com/en/3.0/topics/cache/#the-per-view-cache) cache
- [Template fragment](https://docs.djangoproject.com/en/3.0/topics/cache/#template-fragment-caching) cache
- [Low-level](https://docs.djangoproject.com/en/3.0/topics/cache/#the-low-level-cache-api) cache API

TODO: why not just cache EVERYTHING?
TODO: when should you use the entire site option? Maybe if you don't have any dynamic content?

### Per-view cache

Rather than wasting precious memory space on caching static pages or dynamic pages that source data from a rapidly changing API, you can cache specific views. This is the approach that we'll use in this article.

The cache itself is based on the URL, so requests to, say, `object/1` and `object/2` will be cached separately.

You can implement this type of cache with the [cache_page](https://docs.djangoproject.com/en/3.0/topics/cache/#django.views.decorators.cache.cache_page) decorator either on the view function directly or in the path within `URLConf`:

```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)
def your_view(request):
    ...

# or

from django.views.decorators.cache import cache_page

urlpatterns = [
    path('object/<int:object_id>/', cache_page(60 * 15)(your_view)),
]
```

TODO: emphasize that 9 times out of 10, this is the approach that you'll want to take

### Template fragment cache

If your templates have parts that change often you'll probably want to leave them out of the cache. For example, perhaps you use the authenticated user's email in the navigation bar in an area of the template. Well, If you have thousands of users then that template fragment will be duplicated thousands of times in RAM, one for each user. This is where template fragment caching play, which allows you to specify the specific areas of a template to cache.

For example, say you want to cache a list of objects:

```djangotemplate
{% load cache %}

{% cache 500 object_list %}
  <ul>
    {% for object in objects %}
      <li>{{ object.title }}</li>
    {% endfor %}
  </ul>
{% endcache %}
```

Here, `{% load cache %}` gives us access to the `cache` template tag, which expects a cache timeout in seconds (500) along with the name of the cache fragment (`object_list`).

### Low-level cache API

For cases where the previous options don't provide enough granularity, you can use the low-level API to manage individual objects in the cache by cache key.

For example:

```python
from django.core.cache import cache


def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)

    objects = cache.get('objects')

    if objects is None:
        objects = Objects.all()
        cache.set('objects', objects)

    context['objects'] = objects

    return context
```

In this example, you'll want to invalidate (or remove) the cache when objects are added, changed, or removed from the database. One way to manage this is via database signals:

```python
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.core.cache import cache


@receiver(post_delete, sender=Object)
def object_post_delete_handler(sender, **kwargs):
     cache.delete('objects')


@receiver(post_save, sender=Object)
def object_post_save_handler(sender, **kwargs):
    cache.delete('objects')
```

With that, let's look at an example.

## Project Setup

Clone down the base project from the [cache-django-view](TODO) repo, and then check out the base branch:

```sh
$ git clone https://github.com/testdrivenio/cache-django-view.git --branch base --single-branch
$ cd cache-django-view
```

Create a virtual environment and install the requirements:

```sh
$ python -m venv venv
(venv)$ python -m pip install -r requirements.txt
```

Apply the Django migrations, and then start the server:

```
(venv)$ python manage.py migrate
(venv)$ python manage.py runserver
```

Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser of choice to ensure that everything works as expected. You should see:

TODO: add image

Take a quick look at the view in *apicalls/views.py*:

```python
import datetime

import requests
from django.views.generic import TemplateView


BASE_URL = 'https://httpbin.org/'


class ApiCalls(TemplateView):
    template_name = 'apicalls/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response = requests.get(f'{BASE_URL}/delay/2')
        response.raise_for_status()
        context['content'] = 'Results received!'
        context['current_time'] = datetime.datetime.now()
        return context
```

This view makes an HTTP call with `requests` to [httpbin.org](https://httpbin.org). To simulate a long request, the response from the API is delayed for two seconds. So, it should take about two seconds for [http://127.0.0.1:8000](http://127.0.0.1:8000) to render not only on the initial request, but on each subsequent refresh as well. While a two second load is still slow on the initial request, it's not acceptable for subsequent request. Let's fix this by caching the entire view using Django's Per-view cache level with a Memcached type.

Workflow:

1. Make full call to [httpbin.org](https://httpbin.org) on the initial request
2. Cache the view
3. Subsequent requests will then pull from the cache
4. Invalidate the cache

## Memcached with Django

Start by adding [python-memcached](https://github.com/linsomniac/python-memcached) to the *requirements.txt* file:

Update the requirements.txt to look like this:

```
Django==3.0.5
python-memcached==1.59
requests==2.23.0
```

Install the dependencies:

```sh
(venv)$ python -m pip install -r requirements.txt
```

Next, we need to update the settings in *core/settings.py* to enable the Memcached backend:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
```

Here, we added the [MemcachedCache](https://docs.djangoproject.com/en/3.0/topics/cache/#memcached) backend and indicated that Memcached should be running on our local machine on localhost (127.0.0.1) port 11211.

TODO: is this the default for python-memcached? do we not need to manually run it?

Next, to cache the `ApiCalls` view, decorate the view with the `@cache_page` decorator like so:

```python
import datetime

import requests
from django.utils.decorators import method_decorator # NEW
from django.views.decorators.cache import cache_page # NEW
from django.views.generic import TemplateView

BASE_URL = 'https://httpbin.org/'


@method_decorator(cache_page(60 * 5), name='dispatch') # NEW
class ApiCalls(TemplateView):
    template_name = 'apicalls/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        response = requests.get(f'{BASE_URL}/delay/2')
        response.raise_for_status()
        context['content'] = 'Results received!'
        context['current_time'] = datetime.datetime.now()
        return context
```

Since we're using a class-based view, we can't put the decorator directly on the class, so we used a `method_decorator` and specified `dispatch` (as the method to be decorated) for the name argument.

The cache in this example sets a timeout of five minutes for the cache.

Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) in our browser again. The first request will take two seconds. If we then press the "Get new data button", we get the results instantly. Also now we see that the time on the page stays the same between each load.

TODO: want to show the diff between the cached and non-cached view using django debug toolbar? add image of the diff

TODO: also, i don't see much value in showing the red vs green button, cache vs no cache. Maybe show how to use the dummy cache backend for testing the view?

## Conclusion

In this article we talked about the different built-in options in Django for caching as well as the different levels of caching available. We also guided you step-by-step showing how cache a view using Django's Per-view cache with Memcached.
