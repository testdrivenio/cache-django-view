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

- Configure Django to use Memcached as a Cache Backend
- Setup cache on a specific view

## Project Setup

Clone from GitHub

## Types of caching built in in Django
- Memcached (will use this one in the article)
- Database
- File system
- Local memory
- Dummy

## Implement caching in you app
Implement Memcached 

## Caching a view
First with decorator then in urls.py

## Conclusion