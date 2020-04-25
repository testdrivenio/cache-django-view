# Cache a Django View

Sometimes there might be scenarios where getting the data for a View in Django takes a long time. For instance, there might be a couple of API requests needed to get the data. This would cause the corresponding web page to take a long time to load, and potentially a unhappy user of your web app.

If it is not important that the data is updated in real time, it could even be that the data itself seldom updates, it would be a good case to implement some caching to the View.

In this article I will show you how you can do just that to one of your Django Views.

*Dependencies:*

1. Django v3.0.5
2. Python v3.8.0
3. Python-memcached v1.59
4. Requests v2.23.0


## Objectives

By the end of this tutorial, you should be able to:

- Know an overview of the built-in options available for caching in Django
- Configure Django to use Memcached as a Cache Backend
- Setup cache on a specific view

## Project Setup

Clone down the base project from the cache-django-view repo, and then check out the base branch:

``` 
$ git clone https://github.com/testdrivenio/cache-django-view.git --branch base --single-branch
$ cd cache-django-view
```

Create a virtual environment and install the requirements:

```
$ python -m venv venv
$ python -m pip install -r requirements.txt
```

Do the Django migration, and start the server:

```
$ python manage.py migrate
$ python manage.py runserver 
```

Go to [http://127.0.0.1:8000](http://127.0.0.1:8000) to see that everything works. We should get a web page with the title "Below is the result of the APICall".


## Types of caching built in in Django

Django comes with several built-in cache backends, as well as options for custom backends. The built in options is:

**Memcached (which we'll use in this article)**

Memcached is an entirely memory-based key-value store for small chunks of data. It has the ability to share a cache over multiple servers.

**Database**

Here the cache fragments is stored in a database. A table for that purpose can created with one of the django-admin commands.

**File system**

Saves the cache in separate files for each cache value.

**Local memory**

A local memory chache best suited for development enviroment.

**Dummy**

A "dummy" cache that doesn't cache anything, and just implements the cache interface. Meant to be used in development when you don't want caching, but do not wish to change the code.

## Different levels of caching in Django

Caching in Django can be implemented on different levels. For example you can cache the entire site, or cache more granulary with:

- Per-view cache
- Template fragment caching
- Low-level cache API

### Per-view cache

This is what we'll use in this article. It sets up a cache for a certain view. It depends on which URL is accessing the view. For example in a detail view, `object/1` will be cached separately from `object/2`. The per-view cache can be configured by using a decorator on the view method, or directly on a path in the URLConf.

### Template fragment caching

This gives us the option to cache just a fragment of a template. For instance to cache an image in a template 

```djangotemplate
{% load cache %}
{% cache 300 my_picture %}
    <img src="{% static 'img/my_picture.png' %}">
{% endcache %}
```

Here we first use `{% load cache %}` to be able to access the cache tag. The cache tag expects at least a cache timeout in seconds, together with the name of the cache fragment.

### Low-level cache API

For cases where the previous options don't give enough granularity, we can use the low-level API. We can use the methods of `django.core.cache` and its different methods to control our caches in detail. Examples of cache methods:

- cache.get
- cache.set
- cache.add
- cache.delete
- cahce.clear

To create a cache entry we could use:

```python
from django.core.cache import cache

cache.set("my_key", "The cached value", 60)
```

This creates the key `my_key` (in `django.core.cache.caches`) with the value `The cached value`, and a timeout of 1 minute.

## Implement caching of a view in Django

In the sample project for this article, we have a view that calls an external API. It takes 2 seconds to get the response. This is setup by using `requests` to call a sampe API at [http://httpbin.org](http://httpbin.org). We're calling the `delay` function with a parameter of 2 (seconds).

To have a look at how it currently works, run:

`$ python manage.py runserver`

Then go to [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser, it should take 2 seconds for the pages to show. Each refresh of the web page will do the same. Lets fix that by chaching this view.

We will use the Memcached option in this article to implement caching of a view. To do this we first need to add the `python-memcached` to our dependencies. 


### Setting up requirements

Update the requirements.txt to look like this:

``` 
Django==3.0.5
requests==2.23.0
python-memcached==1.59
```

Update the virtual environment.

`$ python -m pip install -r requirements.txt`

### Declaring our backend

Next we need to update our `core/settings.py` to enable the Memcached backend. Add the following to the settings file:

``` 
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
```

We're telling Django to use the `django.core.cache.backends.memcached.MemcachedCache` backend, and declaring that Memcached should run on our local machine on port 11211.

### Caching the view
Next let's look at our view at `apicalls/views`

```python
import datetime

import requests
from django.views.generic import TemplateView

BASE_URL = 'https://httpbin.org/'


class ApiCalls(TemplateView):
    template_name = 'apicalls/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # request will have response after 2 seconds
        response = requests.get(f'{BASE_URL}/delay/2')
        response.raise_for_status()
        context['content'] = 'Results received!'
        context['current_time'] = datetime.datetime.now()
        return context
```

We have a simple `TemplateView` that makes a sample API request that takes 2 seconds to return a response. To cache this view, all we have to do is to import `chace_page` from `django.views.decorators.cache`, and decorate our view with the `@cache_page` decorator. Edit the `views.py` file to look like this.

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
        # request will have response after 2 seconds
        response = requests.get(f'{BASE_URL}/delay/2')
        response.raise_for_status()
        context['content'] = 'Results received!'
        context['current_time'] = datetime.datetime.now()
        return context
```

Since we're using a classed based view in this example, we can't put the decorator directly on the class. An option is to put it on an overridden `dispatch` method, or as we do here, use the `method_decorator` and specify `dispatch` (as the method to be decorated) for the name argument.

The cache in this example sets a timeout of 5 minutes for the cache.

If we now go to [http://127.0.0.1:8000](http://127.0.0.1:8000) in our browser, the first request will take 2 seconds. If we then press the "Get new data button", we get the results instantly. Also now we see that the time on the page stays the same between each load.

As an option to use the decorator in `apicalls/views.py` we can apply the caching in `apicalls/urls.py`. Remove the three lines of code we added to views and edit the `apicalls/urls.py` to look like this.

```python
from django.urls import path
from django.views.decorators.cache import cache_page # NEW

from .views import ApiCalls

urlpatterns = [
    path('', cache_page(60 * 5)(ApiCalls.as_view()), name='api_results'), # UPDATED
]
```
Here we are decorating the `as_view` method of our ApiCalls view with `cache_page` and are setting the timeout to 5 minutes.

To make it easier to demonstrate the difference between our chached view, and the uncached view, add a new path to `apicalls/urls.py`.

```python
from django.urls import path
from django.views.decorators.cache import cache_page

from .views import ApiCalls

urlpatterns = [
    path('', cache_page(60 * 15)(ApiCalls.as_view()), name='api_results'),
    path('uncached/', ApiCalls.as_view(), name='api_results_uncached'), # NEW
]
```

Also add new button after the existing button in `templates/apicalls/home.html`.

```html
 <a href="{% url 'api_results_uncached' %}">
    <button type="button" class="btn btn-danger">
        Get new data (uncached)
    </button>
 </a>
```

Restart the Django server by first stopping it with `CTRL-C` in the terminal where it is started, and then run:

```
$ python manage.py runserver
```
If we now go to [http://127.0.0.1:8000](http://127.0.0.1:8000) in our browser, we should see two buttons. The green button reloads the cached page, and the red loads the unchached page (takes 2 seconds). We can also see that the time updates when pressing the red button, but pressing the green button should give a previous time when the cache was saved.


## Conclusion

In this article we talked about the different built-in options in Django for caching, as well as the different level of caching available. We also guided you step by step how to set up a cache on a view. First by using a decorator on the view, and then how to do it directly in the URLConf.

Looking for more?

- [Django’s cache framework](https://docs.djangoproject.com/en/3.0/topics/cache/)
