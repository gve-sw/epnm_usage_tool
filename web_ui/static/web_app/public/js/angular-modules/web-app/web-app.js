/* Global variables */

var appModule = angular.module('appModule',['ngRoute','ngAnimate'])

/*  Configuration    */

// To avoid conflicts with other template tools such as Jinja2, all between {a a} will be managed by ansible instead of {{ }}
appModule.config(['$interpolateProvider', function($interpolateProvider) {
  $interpolateProvider.startSymbol('{a');
  $interpolateProvider.endSymbol('a}');
}]);


// Application routing
appModule.config(function($routeProvider, $locationProvider){
    // Maps the URLs to the templates located in the server
    $routeProvider
        .when('/', {templateUrl: 'ng/main'})
        .when('/main', {templateUrl: 'ng/main'})
        .when('/login', {templateUrl: 'login'})
        .when('/location/:loc', {
            templateUrl: function(params) {
                return 'ng/location/' + params.loc ;
            }
        })
        .when('/alarms/:location', {
            templateUrl: function(params) {
                return 'ng/alarms/' + params.location ;
            }
        })
        .when('/device/:dev', {
            templateUrl: function(params) {
                return 'ng/device/' + params.dev ;
            }
        })
       
    $locationProvider.html5Mode(true);
});


/*  Controllers    */

appModule.controller('PostCtrl', ['$scope', '$routeParams', function($scope, $routeParams) {
    $scope.templateUrl = 'ng/location/'+$routeParams.loc;
}]);

// App controller is in charge of managing all services for the application
appModule.controller('AppController', function($scope, $location, $http, $window, $rootScope){

    $scope.example = {text:""};
    $scope.error = ""
    $scope.loading = false;

    $scope.go = function ( path ) {
        $location.path( path );
    };


    $scope.clearError = function(){
        $scope.error = "";
    };

    $scope.sendExample = function(){
        $scope.loading = true;
        $http
            .post('api/example', {'example': $scope.example })
            .then(function (response, status, headers, config){
               $scope.example.reply = response.data.response
            })
            .catch(function(response, status, headers, config){
                $scope.error = response.data.message
            })
            .finally(function(){
                $scope.loading = false;
            })
    };
});
