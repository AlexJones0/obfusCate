#include <stdio.h>
int main()
{
  int x;
  char y;
  int b = 1;
  a:
  while (b != 0)
  {
    switch (b)
    {
      case 5:
        switch (y)
      {
        case 'x':
          goto g;

        case 'y':
          goto h;

        default:
          goto i;

        case 'a':
          goto j;

        case 'd':
          goto k;

      }

        b = 6;
        break;

      case 4:
        c:
      x = 5;

        b = 3;
        break;
        d:
      x = 4;

        e:
      x = 3;

        f:
      x = 1;

        b = 3;
        break;
        b = 3;
        break;

      case 7:
        g:
      y = 'y';

        h:
      y = 'z';

        i:
      y = '3';

        j:
      y = '9';

        k:
      y = '7';

        b = 6;
        break;

      case 6:
        printf("%d %d\n", x, y);
        b = 0;
        break;

      case 1:
        x = 2;
        b = 2;
        break;

      case 3:
        y = 'e';
        b = 5;
        break;

      case 2:
        switch (x)
      {
        case 3:
          goto c;

        case 4:
          goto c;

        default:
          goto d;

        case 6:
          goto e;

        case 2:
          goto f;

      }

        b = 3;
        break;

    }

  }


}

