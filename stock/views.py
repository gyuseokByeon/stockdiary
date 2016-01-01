# -.- coding: utf-8 -.-
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from bs4 import BeautifulSoup
import urllib
from stock.models import *
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.db.models import F
from django.core.urlresolvers import reverse, reverse_lazy

STOCK_URL = 'http://finance.naver.com/item/main.nhn?code='
login_url = '/stock/login'

def home(request):
	return HttpResponseRedirect('/stock/list')
	
def list(request):
	objs = Stock.objects.order_by('stock_code')
	return render_to_response('stock/stock_list.html',RequestContext(request,{'stocks':objs}))

def stock_id(request, id):
	url = STOCK_URL+id
	html = urllib.urlopen(url)
	soup = BeautifulSoup(html)
	
	stock_id=id
	blind = soup.find('dl',{'class':'blind'})
	
	stock_dd= blind.find_all('dd')
	stock_name=stock_dd[1].text[4:]
	stock_price=stock_dd[3].text.split()[1]
	stock_price=stock_price.replace(',','')
	stock_content=blind
	stock_image = soup.find_all('img',{'id':'img_cahrt_area'})
	stock_gubun = stock_dd[2].text[-3:]

	stock_informs = soup.find_all('em')

	pbr = per = cns_per = cns_eps = ''
	for info in stock_informs:
		try:
			if info['id']=='_pbr':
				pbr=info.text
			if info['id']=='_per':
				per=info.text
			if info['id']=='_cns_per':
				cns_per=info.text
			if info['id']=='_cns_eps':
				cns_eps=info.text

		except KeyError:
			pass

	per = per.replace(',','')
	pbr = pbr.replace(',','')
	cns_eps = cns_eps.replace(',','')
	cns_per = cns_per.replace(',','')

	if per=='':
		per=0.0
	if pbr=='':
		pbr=0.0
	if cns_eps=='':
		cns_eps=0.0
	if cns_per=='':
		cns_per=0.0

	try:
		year = datetime.today().year
		stock = Stock.objects.filter(stock_code=stock_id)[0]
		if stock:
			stock_infos = StockInform.objects.filter(stock_code=stock, year=year)
			if stock_infos:
				stock_info = stock_infos[0]
				stock_info.per = per
				stock_info.pbr = pbr
				stock_info.cns_per = cns_per
				stock_info.cns_eps = cns_eps
				stock_info.save()
			else:
				stock_info, created = StockInform.objects.get_or_create(stock_code=stock, 
					year= year,
					per = per,
					pbr = pbr,
					cns_per = cns_per,
					cns_eps = cns_eps
					)
	except KeyError:
		pass


	variable = RequestContext(request,{
		'stock_id':stock_id,
		'stock_name':stock_name,
		'stock_price':stock_price,
		'stock_content':stock_content.text,
		'stock_image' : stock_image[0]['src'],
		'stock_gubun' : stock_gubun,
		'pbr' : pbr,
		'per' : per,
		'cns_per' : cns_per,
		'cns_eps' : cns_eps,
		})
	return render_to_response('stock/stock_id.html', variable)

def stock_add(request):
	stock_code = request.POST['stock_code']
	stock_name = request.POST['stock_name']
	stock_gubun = request.POST['stock_gubun']
	stock, created = Stock.objects.get_or_create(stock_code=stock_code)
	stock.stock_name=stock_name
	stock.stock_gubun=stock_gubun
	stock.save()
	return HttpResponseRedirect(reverse('stock:list'))

def stock_extract(request, classid):
	url='http://paxnet.moneta.co.kr/stock/searchStock/searchStock.jsp?section='+classid
	html = urllib.urlopen(url)
	soup = BeautifulSoup(html)
	
	stock_links = soup.find_all('a')
	
	for stock_link in stock_links:
		try:
			if stock_link['href'].__contains__('http://paxnet.asiae.co.kr/asiae/stockIntro/indCurrent.jsp?code='):
				stock_code=stock_link['href'][-6:]
				stock_name=stock_link.text
				stock, created = Stock.objects.get_or_create(stock_code=stock_code)
				stock.stock_name=stock_name
				if classid=='0':
					stock.stock_gubun = "코스피"
				else:
					stock.stock_gubun = "코스닥"
				
				stock.save()
		except KeyError:
			pass

	return HttpResponseRedirect('/stock/list')

@login_required
def stock_delete_all(request):
	if request.user.is_staff:
		Stock.objects.all().delete()
	return HttpResponseRedirect('/stock/list')

def stock_search(request):
	search_word=request.POST['search_key']
	if search_word:
		if len(search_word)>6:
			stock_code = search_word[:6]
			return HttpResponseRedirect(reverse('stock:stock_id',args=[stock_code]))

	return HttpResponseRedirect('/stock/list')

def search_stock(request):
	objs = Stock.objects.all()
	stock_items = []
	_pbr = 3
	_per_from = 10
	_per_to = 30

	if request.POST:
		if request.POST['pbr']=='':
			_pbr=9999
		else:
			_pbr = request.POST['pbr']
		
		if request.POST['per_from']=='':
			_per_from=-9999
		else:		
			_per_from = request.POST['per_from']

		if request.POST['per_to']=='':
			_per_to=9999
		else:		
			_per_to = request.POST['per_to']

		stock_items = StockInform.objects.filter(pbr__lt=_pbr).filter(per__gt=_per_from).filter(per__lt=_per_to)


	variable = RequestContext(request,{
		'stocks':objs,
		'stock_items':stock_items,
		'pbr' : _pbr,
		'per_from' : _per_from,
		'per_to' : _per_to,
		})
	return render_to_response('stock/search_stock.html', variable)


def tweet_send(request):
	if request.POST:
		tweet_id = request.POST['tweet_id']
		tweet_text = request.POST['tweet_text']
		import tweet
		try:
			tweet.api.send_direct_message(screen_name=tweet_id,text=tweet_text)
		except:
			pass
	return render_to_response('stock/tweet.html',RequestContext(request))

def alarm(request):
	alarm_list = AlarmStock.objects.filter(alarm_user=request.user)
	print alarm_list
	return render_to_response('stock/stock_alarm.html',RequestContext(request,{'alarm_list':alarm_list}))

def alarm_add(request):
	if request.POST:
		stock_code = request.POST['stock_code']
		stock = Stock.objects.filter(stock_code = stock_code)
		price = request.POST['price']
		qty = request.POST['qty']
		goal_price = request.POST['goal_price']
		alarm_stock, created  = AlarmStock.objects.get_or_create(
			alarm_user = request.user, 
			stock_code = stock[0],
			price = price,
			qty = qty,
			goal_price = goal_price,
			)
	return render_to_response('stock/stock_alarm.html',RequestContext(request))


@login_required()
def favorite(request):
	favorites = Favorite.objects.filter(stock_user=request.user)


	objs = Stock.objects.all()
	variable = RequestContext(request,{
		'stocks' : objs,
		'favorites' : favorites,
		})
		
	return render_to_response('stock/favorites.html',variable)

@login_required()
def favorite_add(request):
	if request.POST:
		# user_id = request.POST['user_id']
		stock_code = request.POST['stock_code']

		user_error = stock_error = False
		# user = User.objects.filter(username=user_id)
		user = request.user
		if user:			
			user_error = False
		else:
			user_error = True

		stock = Stock.objects.filter(stock_code=stock_code)
		if stock is None:
			stock_error = True


		if user_error or stock_error:
			return render_to_response('stock/favorite_add.html')

		else:
			favorite, created = Favorite.objects.get_or_create(stock_user=user, stock_code=stock[0])
			# return HttpResponseRedirect(reverse_lazy('stock:favorite'))
			return HttpResponseRedirect('/stock/favorite')
	else:
		return render_to_response('stock/favorite_add.html',RequestContext(request))


@login_required()
def favorite_delete(request, stock_code):
	# user =  User.objects.filter(username=user_id)
	stock = Stock.objects.filter(stock_code=stock_code)
	favorite = Favorite.objects.filter(stock_user=request.user, stock_code=stock)
	favorite.delete()
		
	return HttpResponseRedirect('/stock/favorite')


def today_stock(request):
	stock_items = []
	
	stock = StockFilter.objects.filter(filter_name='todaystock')
	_pbr_from = stock[0].pbr_from
	_pbr_to = stock[0].pbr_to
	_per_from = stock[0].cns_per_from
	_per_to = stock[0].cns_per_to
	
	# print _pbr_from
	stock_items = StockInform.objects.filter(
		pbr__gt=_pbr_from, 
		pbr__lt=_pbr_to, 
		cns_per__gt=_per_from, 
		cns_per__lt=_per_to,
		)

	variable = RequestContext(request,{
		'stock_items':stock_items,
		})
	return render_to_response('stock/today.html',variable)