from django.db import models

# Create your models here.
class epnm_info(models.Model):
	host = ''
	user = ''
	password = ''

	def get_info(self):
		r_dict={
			'host'		: self.host,
			'user'		: self.user,
			'password'	: self.password,
		}
		return r_dict
