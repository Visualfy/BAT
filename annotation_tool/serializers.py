from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import serializers
from django.utils import timezone
import colorsys
from aiorest_ws.utils.fields import to_choices_dict, flatten_choices_dict
from annotation_tool import models

id = 'root'
Class, created = models.Class.objects.get_or_create(name=id)

if created:
    Class.root = Class
    Class.save()

class ProjectSerializer(serializers.Serializer):
    project_name = serializers.CharField(label='Project name', max_length=50)
    overlap = serializers.BooleanField(label='Allow class overlap in this project', default=False)
    classes = serializers.MultipleChoiceField(choices=[])

    rootID = 1 #TODO fix first class. To be null or root or something like that.

    # Creation of the project and the required ClassInstance objects
    def create(self, validated_data):
        project = models.Project(name=validated_data['project_name'],
                                 overlap=validated_data['overlap'],
                                 creation_date=timezone.now())
        project.save()
        n_colors = len(validated_data['classes'])
        colors = []
        for i in xrange(n_colors):
            colors.append(colorsys.hsv_to_rgb(i / float(n_colors), 1, 1))

        classes = models.Class.objects.all()

        for i, class_name in enumerate(sorted(validated_data['classes'])):

            rgba_color = "rgba(%d, %d, %d, 0.5)" % (255 * colors[i][0],
                                                    255 * colors[i][1],
                                                    255 * colors[i][2])

            c = models.Class.objects.get(name=class_name) # This line get selected classes

            c.childs = self.getChildClass(classes, c.id)

            if c.childs:
                self.createCiChildClass(c.childs, rgba_color, project)

            ci = models.ClassInstance.objects.create(
                project=project,
                class_obj=c,
                shortcut=c.id, #TODO: Are you sure than this won't breack the app?
                color=rgba_color
            )

            ci.save()

        return project

    # This function creates a recursively class instance of the passed class
    # and all the children found in it.
    def createCiChildClass(self, childs, rgba_color, project):
        for cclass in childs:
            ci = models.ClassInstance.objects.create(
                project=project,
                class_obj=cclass,
                shortcut=cclass.id,  # TODO: Are you sure than this won't breack the app?
                color=rgba_color
            )

            ci.save()

            self.createCiChildClass(cclass.childs, rgba_color, project)

    # This function GETS the children recursively and adds them to the
    # "childs" attribute of the corresponding class.
    def getChildClass (self, classes, rootID):
        classChildTree = filter(lambda x: x.root.id == rootID and x.root.id != self.rootID, classes)

        for cclass in classChildTree:
            cclass.childs = self.getChildClass(classes, cclass.id)

        return classChildTree

    # All the names of Class objects are loaded to the classes field
    # http://programtalk.com/python-examples/aiorest_ws.utils.fields.flatten_choices_dict/
    def __init__(self, *args, **kwargs):
        classes = models.Class.objects.filter(root=1).exclude(name=self.rootID)
        class_dict = dict([(c.name, c.id) for c in classes])
        self.fields['classes'].grouped_choices = to_choices_dict(class_dict)
        self.fields['classes'].choices = flatten_choices_dict(self.fields['classes'].grouped_choices)
        self.fields['classes'].choice_strings_to_values = {
            key: key for key in self.fields['classes'].choices.keys()
        }
        self.fields['classes'].allow_blank = kwargs.pop('allow_blank', False)
        super(ProjectSerializer, self).__init__(*args, **kwargs)

        # Find Childs of all class and create a tree structure //TODO: comment when not necessary
        classesWhereFind = models.Class.objects.all()
        classTree = filter(lambda x: x.root.id == self.rootID, classesWhereFind)

        for cclass in classTree:
            cclass.childs = self.getChildClass(classesWhereFind, cclass.id)
        #
        # for cclass in classTree:
        #     logging.debug(cclass.childs)
        #     for cclass2 in cclass.childs:
        #         logging.debug(cclass2.childs)



class TagSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)


class ClassSerializer(serializers.Serializer):
    name = serializers.CharField(label='Class name', max_length=50)
    classes = serializers.ChoiceField(label='Root Class',choices=[])

    # newClass = models.Class.create('newClass', 1)
    # logging.debug(newClass)

    def validate(self, data):
        objects = models.Class.objects.filter(name=data.get('name'))
        if objects:
            raise serializers.ValidationError('Class with current params already exists.')

        return data

    def create(self, validated_data):
        validated_data['name'] = validated_data['name'].replace(' ', '_')
        validated_data['root'] = models.Class.objects.get(name=validated_data['classes'])
        del validated_data['classes']
        class_object = models.Class(**validated_data)
        class_object.save()
        return class_object

    def __init__(self, *args, **kwargs):
        classes = models.Class.objects.all()
        class_dict = dict([(c.name, c.id) for c in classes])
        self.fields['classes'].grouped_choices = to_choices_dict(class_dict)
        self.fields['classes'].choices = flatten_choices_dict(self.fields['classes'].grouped_choices)
        self.fields['classes'].choice_strings_to_values = {
            key: key for key in self.fields['classes'].choices.keys()
        }
        self.fields['classes'].allow_blank = kwargs.pop('allow_blank', False)
        super(ClassSerializer,self).__init__(*args, **kwargs)

class UploadDataSerializer(serializers.Serializer):
    project = serializers.PrimaryKeyRelatedField(queryset=models.Project.objects.all())
    segments_length = serializers.FloatField(label='Segment length')
    upload_file_field = serializers.FileField(style={'template': 'fields/_file_field.html'})


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(label='Username',
                                     max_length=50)
    password = serializers.CharField(label='Password',
                                     max_length=50,
                                     style={'input_type': 'password'})


class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(label='Username',
                                     max_length=50)
    password = serializers.CharField(label='Password',
                                     max_length=50,
                                     style={'input_type': 'password'})
    confirm_password = serializers.CharField(label='Confirm password',
                                             max_length=50,
                                             style={'input_type': 'password'})

    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError('Those passwords don\'t match.')

        try:
            models.User.objects.get(username=data.get('username'))
        except models.User.DoesNotExist:
            pass
        else:
            raise serializers.ValidationError('User already exists.')

        return data

    def create(self, validated_data):
        user = models.User(username=validated_data['username'])
        user.set_password(self.validated_data['password'])
        user.save()
        return user


#class ClassProminenceSerializer(serializers.Serializer):
#    region = serializers.PrimaryKeyRelatedField(queryset=models.Region.objects.all())
#    class_obj = serializers.PrimaryKeyRelatedField(queryset=models.Class.objects.all())
#    prominence = serializers.IntegerField(required=False,
#                                          min_value=models.ClassProminence.VERY_LOW,
#                                          max_value=models.ClassProminence.VERY_LOUD)
#
#    def create(self, validated_data):
#        obj = models.ClassProminence(**validated_data)
#        obj.save()
#        return obj


#class RegionSerializer(serializers.Serializer):
#    annotation = serializers.PrimaryKeyRelatedField(queryset=models.Annotation.objects.all())
#    start_time = serializers.FloatField()
#    end_time = serializers.FloatField()
#    tags = TagSerializer(many=True)
#    color = serializers.CharField(max_length=50, allow_blank=True)
#    classes = serializers.CharField()

#    def create(self, validated_data):
#        classes = validated_data.pop('classes')
#        validated_data.pop('tags')
#
#        region = models.Region(**validated_data)
#        region.save()
#
#        # add tags
#        if 'tags[]' in self.initial_data:
#            tags = dict(self.initial_data)['tags[]']
#            tags = map(lambda name: models.Tag.objects.get_or_create(name=name)[0], tags)
#            region.tags.add(*tags)
#
#        # add classes
#        classes = map(lambda name: models.Class.objects.get(name=name, project=region.get_project()), classes.split())
#        for class_obj in classes:
#            data = {'region': region.id, 'class_obj': class_obj.id}
#            class_prominence = ClassProminenceSerializer(data=data)
#            class_prominence.is_valid(raise_exception=True)
#            class_prominence.save()
#
#        return region
